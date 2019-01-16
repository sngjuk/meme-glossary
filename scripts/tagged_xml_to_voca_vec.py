#!/usr/bin/env python3

#from service.client import BertClient
from numpy import dot
from numpy.linalg import norm
import os
import gensim
from lxml import objectify
import subprocess
import sent2vec
import numpy as np
import sys
import argparse
import re

#requires : sentence embedding -- input : model_bin, xml_folder, vec_out_dir
def get_args_parser():
    parser = argparse.ArgumentParser(description='Directories for processing')
    parser.add_argument('-model_path', type=str, default='/root/shared_data/model/my_model_lr5_ngram1_epch11.bin', 
                        required=True, help='path of a input images.')
    parser.add_argument('-xml_path', type=str, default='/root/shared_data/lee_cut_filt_xml/', 
                        required=True, help='path of a output xml.')
    parser.add_argument('-vec_file_name', type=str, default='/root/shared_data/embedding/fast_sent.vec', 
                        required=True, help='path of a output xml.')
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
      parser.print_help()
      sys.exit()

    return args

def xml2vec(args):
    model = sent2vec.Sent2vecModel()
    model_dir = args.model_path
    model.load_model(model_dir)

    print('model load done')
    in_dir = args.xml_path
    out_dir = args.vec_file_name
    out_dir_ = out_dir.rsplit('/',1)[0]
    print('out vector directory : %s' %(out_dir_))
    
    if not os.path.exists(out_dir_):
      os.makedirs(out_dir_)

    # Reads xml file and generating .vec file (gensim format) _
    num_word = 0
    vec_size = None

    episodes = os.listdir(in_dir)
    flag=True
    # Read tags from xml file. 
    # Counting non zero vector results in inefficient way.
    for episode in episodes:
      if not os.path.isdir(in_dir+episode):
        continue
      xmls = os.listdir(in_dir + episode)
      
      for i in xmls:
        path = str(in_dir)+str(episode)+'/'+str(i)    
        if not path.lower().endswith(('.xml')):
          continue 
        f = open(in_dir+episode+'/'+str(i))
        xml_string = f.read()
        if not xml_string:
          print('not xml string?')
          continue
        root = objectify.fromstring(xml_string)
        q_str = str(root['object']['name'])
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\n{1,}', ' ', q_str)
        q_str = re.sub(r'\s{1,}', ' ', q_str)
        q_str = re.search(r'\s{0,}(.*)', q_str).group(1)
        if q_str:
          emb = model.embed_sentence(q_str)
          if flag:
            vec_size=len(emb[0])
            flag=False
          if(np.any(emb)):        
            num_word+=1
        f.close()

    # Writing to .vec file.
    ff = open(out_dir, 'w')
    ff.write(str(num_word)+' '+str(vec_size) +'\n')

    for episode in episodes:
      xmls = os.listdir(in_dir+episode)
      for i in xmls:
        path = in_dir+episode+'/'+i    
        if not path.lower().endswith(('.xml')):
          continue

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
        if q_str:
          emb = model.embed_sentence(q_str)
          if(np.any(emb)):
            ff.write(os.path.abspath(path) +' ')
            for e in emb[0]:
              ff.write(str(e) + ' ')
            ff.write('\n')
            print(str(i) + ' ' + str(q_str))    
        f.close()
    ff.close()
    print('writing .vec done')

def main():
    args = get_args_parser()
    print(args)
    xml2vec(args)

if __name__ == "__main__":
    main()
