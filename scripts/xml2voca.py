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

#requires : sentence embedding -- input : model_bin, xml_folder, vec_out_dir

model = sent2vec.Sent2vecModel()
model_dir = '/root/shared_data/model/'
model_name = 'my_model_lr5_ngram1_epch11.bin'
model_dir+=model_name
#model_name = 'my_model.bin'

model.load_model(model_dir)

in_dir = sys.argv[1]
xmlpath = '/root/shared_data/lee_cut_filt_xml/'
in_dir = xmlpath

out_dir = '/root/shared_data/embedding/'
if not os.path.exists(out_dir):
  os.makedirs(out_dir)

#bert 
'''
bc = BertClient(ip='172.17.0.2')
test_res = bc.encode(['안녕하세요 이것은 예시 문장입니다.'])
num_word = len(episodes)
vec_size= len(test_res[0])
print('vec_size ' +str(vec_size))
out_dir = '../gitdir/bert_embed/'
'''

#takes in [xml] file, outputs .vec
#out_dir += 'bert_small.txt'
print('model load done')

# Reads xml file and generating .vec file (gensim format) _
vec_file_name = 'fast_sent.vec'
num_word = 0
vec_size = 700

#for bert usage.
'''
for i in episodes:
    f = open(in_dir+str(i))
    print(str(i) +' ', end='')
    xml_string = f.read()
    root = objectify.fromstring(xml_string)
    q_str = str(root['object']['name']).replace('\t','').replace('\n','')
    #q_str += ' '
    #q_str = (q_str +' ')*15
    print(q_str)
    st_vec = bc.encode([q_str])
    ff.write(str(i) +' ')
    for e in st_vec[0]:
        ff.write(str(e) + ' ')
    ff.write('\n')
'''

episodes = os.listdir(in_dir)

# read tags from xml file. counting non zero vector results.
for episode in episodes:
  if not os.path.isdir(in_dir+episode):
    continue
  xmls = os.listdir(in_dir + episode)
  for i in xmls:
    f = open(in_dir+episode+'/'+str(i))
    xml_string = f.read()
    if not xml_string:
      continue
    root = objectify.fromstring(xml_string)
    q_str = str(root['object']['name']).replace('\t','').replace('\n','').replace(',','').replace('!','').replace('?','')
    if q_str:
      emb = model.embed_sentence(q_str)    
      if(np.any(emb)):
        num_word+=1
    f.close()

# writing to .vec file.
ff = open(out_dir+vec_file_name, 'w')
ff.write(str(num_word)+' '+str(vec_size) +'\n')

for episode in episodes:
  xmls = os.listdir(in_dir+episode)
  for i in xmls:
    f = open(in_dir+episode+'/'+str(i))
    xml_string = f.read()
    if not xml_string:
      continue
    root = objectify.fromstring(xml_string)
    q_str = str(root['object']['name']).replace('\t','').replace('\n','').replace(',','').replace('!','').replace('?','')
    if q_str:
      emb = model.embed_sentence(q_str)
      if(np.any(emb)):
        ff.write(str(i) +' ')
        for e in emb[0]:
          ff.write(str(e) + ' ')
        ff.write('\n')
        print(str(i) + ' ' + str(q_str))    
    f.close()
ff.close()

print('writing .vec done')
