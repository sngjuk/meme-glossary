#!/usr/bin/env python3
'''
Generate .vec voca file from image xml folder. (voca format is KeyedVectors.load_word2vec_format.) [filename : vector]
Usage : ./xml2vec --model_path=/some_dir/some_model.bin --xml_dir=/some_dir/some_xml/ --vec_path=/some_dir/some_result.vec
'''
import os
from lxml import objectify
import numpy as np
import sys
import argparse
import re
from model import EmbedModel

#requires : sentence embedding -- input : model_bin, xml_folder, vec_out_dir
def get_args_parser():
    parser = argparse.ArgumentParser(description='Paths for processing')
    parser.add_argument('-m', '--model_path', type=str, default='/root/shared_data/model/my_model_lr5_ngram1_epch11.bin', 
                        required=True, help='Path of a model.')
    parser.add_argument('-x', '--xml_dir', type=str, default='/root/shared_data/lee_cut_filt_xml/', 
                        required=True, help='Directory of a input xml.')
    parser.add_argument('-v', '--vec_path', type=str, default='/root/shared_data/embedding/fast_sent.vec', 
                        required=True, help='Path of output .vec file.')
    parser.add_argument('-n', '--include_no_text', type=bool, default=False, help='include no text image.')
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
      parser.print_help()
      sys.exit()
    return args

def xml2vec(args):
    model_path = os.path.abspath(args.model_path)
    in_dir = os.path.abspath(args.xml_dir) + '/'
    out_path = os.path.abspath(args.vec_path)
    no_txt_flag = args.include_no_text
    
    print('model dir : ', model_path)
    model = EmbedModel()
    model.load_model(model_path)
    print('model load done')
    
    out_dir = out_path.rsplit('/',1)[0]
    print('out vector directory : %s' %(out_dir))
    if not os.path.exists(out_dir):
      os.makedirs(out_dir)

    # Reads xml file and generating .vec file (gensim format) _
    num_word = 0
    vec_size = None
    
    # Writing to .vec file.
    vecfile_content = ''
    flag=True
    episodes = os.listdir(in_dir)

    for episode in episodes:
      xmls = os.listdir(in_dir+episode)
      for i in xmls:
        path = in_dir+episode+'/'+i    
        if not path.lower().endswith(('.xml')):
          continue

        # open .xml
        f = open(in_dir+episode+'/'+str(i))
        xml_string = f.read()
        if not xml_string:
          continue
        
        root = objectify.fromstring(xml_string)
        q_str = str(root['object']['name'])
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\s{1,}', ' ', q_str)
        q_str = re.search(r'\s{0,}(.*)', q_str).group(1)
        
        if q_str or no_txt_flag:
          emb = model.embed_sentence(q_str)
          # if vector is retrieved.
          if np.any(emb) or no_txt_flag:
            if flag:
              vec_size=len(emb[0])
              flag=False

            vecfile_content += os.path.abspath(path) +' '
            for vec in emb[0]:
              vecfile_content += (str(vec) + ' ')
            vecfile_content += '\n'
            num_word+=1
            print(str(i) + ' ' + str(q_str))    
        f.close()

    with open(out_path, 'w') as vec_file:
      vec_file.write(str(num_word)+' '+str(vec_size) +'\n')    
      vec_file.write(vecfile_content)
    print('writing .vec done.')

def main():
    args = get_args_parser()
    print(args)
    xml2vec(args)

if __name__ == "__main__":
    main()
