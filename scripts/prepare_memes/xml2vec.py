#!/usr/bin/env python3
'''
Generate .vec voca file from image xml folder. (voca format is KeyedVectors.load_word2vec_format.) [filename : vector]
Usage : ./xml2vec --model_path=./model.bin --meme_dir=./meme_cut/ --xml_dir=./xml_dir/ --vec_path=./voca.vec
'''
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from lxml import objectify
import numpy as np
import argparse
import re
from server.nlp.model import EmbedModel

# requires : sentence embedding -- input : model_bin, xml_folder, vec_out_dir
def get_args_parser():
    parser = argparse.ArgumentParser(description='Paths for processing')
    parser.add_argument('-m', '--model_path', type=str, default='./model.bin',
                        required=True, help='Path of model.')
    parser.add_argument('-i', '--meme_dir', type=str, required=True,
                        help='Directory of cut images. e.g ./3_manual_filtered_cut/')
    parser.add_argument('-x', '--xml_dir', type=str, required=True,
                        help='Directory of xml labels. e.g ./4_label_xml/')
    parser.add_argument('-v', '--vec_path', type=str, required=True,
                        help='Path of output .vec file. e.g ./5_test_meme_voca.vec')
    parser.add_argument('-n', '--include_no_text', type=bool, default=False, help='include no text images to vector as zeros.')
    
    args = parser.parse_args()
    return args

def rm_gbg_from_xml(value):
    value = str(value).replace('\t','').replace('\n','')
    value = re.search(r'\s{0,}(.*)', value).group(1)
    return value

def xml2vec(args):
    model_path = os.path.abspath(args.model_path)
    img_dir = os.path.abspath(args.meme_dir) + '/'
    xml_dir = os.path.abspath(args.xml_dir) + '/'
    out_path = os.path.abspath(args.vec_path)
    no_txt_flag = args.include_no_text
    
    print('\nmodel path : ', model_path)
    model = EmbedModel()
    print('loading model...')
    model.load_model(model_path)
    
    out_dir = out_path.rsplit('/',1)[0]
    if not os.path.exists(out_dir):
      os.makedirs(out_dir)

    # Reads xml file and generating .vec file (gensim format)
    num_word = 0
    vec_size = None
    
    # Writing to .vec file.
    vecfile_content = ''
    flag=True
    episodes = os.listdir(xml_dir)

    for episode in episodes:
      xmls = os.listdir(xml_dir+episode)
      print('\n## Episode : ',episode)
      if episode == '.ipynb_checkpoints':
        continue        
        
      for xml_file in xmls:
        path = xml_dir+episode+'/' + xml_file
        rel_path = episode +'/' + xml_file

        if not path.lower().endswith(('.xml')):
          continue

        # open .xml
        f = open(xml_dir+episode+'/'+str(xml_file))
        xml_string = f.read()
        if not xml_string:
          continue

        xml_root = objectify.fromstring(xml_string)
        # label is saved in ['object']['name'].
        q_str = rm_gbg_from_xml(xml_root['object']['name']) 
        '''
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\s{1,}', ' ', q_str)
        q_str = re.search(r'\s{0,}(.*)', q_str).group(1)
        '''
        if q_str or no_txt_flag:
          emb = model.embed_sentence(q_str)
          # if vector is retrieved.
          if np.any(emb) or no_txt_flag:
            if flag:
              vec_size=len(emb[0])
              flag=False
            vecfile_content += rel_path +' '

            for vec in emb[0]:
              vecfile_content += (str(vec) + ' ')
            vecfile_content += '\n'
            num_word+=1
            print(str(xml_file) + ' ' + str(q_str))    
        f.close()

    with open(out_path, 'w') as vec_file:
      vec_file.write(str(num_word)+' '+str(vec_size) +'\n')    
      vec_file.write(vecfile_content)

def main():
    args = get_args_parser()
    xml2vec(args)
    print('\nInclude none-text meme flag: %s' %(str(args.include_no_text)))
    print('Write done : %s\n' %(args.vec_path))
   
if __name__ == "__main__":
    main()
