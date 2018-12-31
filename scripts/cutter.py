#!/usr/bin/env python3

import os
import sys
from subprocess import call
import subprocess
import urllib.parse
import json
import argparse
import io
import os
import re
import PIL.Image
import pathlib

#this script is for image cutting.
km_dir = './'
in_dir = sys.argv[1]
out_dir = sys.argv[2]

episodes = os.listdir(in_dir)
print(episodes)

#execution example -- python3 dir.py kumiko/ input_lee_ori/ out_put/ 
kumi_done_list = []

def resize_img(im, episode):
  for h in range(0, im.height, 2200):
   nim = im.crop((0, h, im.width-1, min(im.height, h+2500)-1))
   num = '%05d' % h
   nim.save(in_dir+episode+'/'+"PartialImage-" + num + ".jpg")
   #display(Image('PartialImage-' +str(h) + '.jpg', width=300, height=300))
   #print('----')

#resize file for kumiko. maximum 2500 pix
def pre_cutter():
  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode+'/')
    imgs.sort()
    imgs2 = []
    for img in imgs:
      if img.lower().endswith(('.png', '.jpg', '.jpeg')):
        imgs2.append(img)
    
    for img in imgs2:
      fp = open(in_dir+episode+'/'+img,"rb")
      im = PIL.Image.open(fp)
      if im.height > 2500:
        resize_img(im, episode)
        os.remove(in_dir+episode+'/'+img)
      fp.close()

def run_kumiko():
  print("in kumiko")
  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode)
    delist = [x for x in imgs if not x.lower().endswith(('.jpg','.jpeg','png'))]
    print('delete ' +str(delist))
    for i in delist:
      os.remove(in_dir+str(episode)+'/'+i)

    proc = subprocess.Popen([str(km_dir)+'kumiko', '-i', str(in_dir)+''+str(episode), '-o', str(in_dir)+str(episode)+'/kumiko_res.json'], stdout=subprocess.PIPE)
    output = proc.stdout.read()
    #f = open(str(in_dir)+str(episode)+'/kumiko_res.json','w')
    #f.write(str(output))
    
def run_cutter():
  episodes = os.listdir(in_dir)
  ep_num = 0
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  
  for idx, episode in enumerate(episodes):
    f = open(str(in_dir)+str(episode)+'/kumiko_res.json')
    json_string = f.read()
    objs = json.loads(json_string)
    inum=0
    images = os.listdir(str(in_dir)+str(episode))
    images2 = []
    for i in images:
      if i.lower().endswith(('.png', '.jpg', '.jpeg')):
        images2.append(i)
    print('current episode! : ' + str(episode))
    images2.sort()
    print(images2)
    
    epi_name = episode.replace(' ', '_').replace('-','_')
    print('replaced folder name ' +str(epi_name))
    images = images2
    directory = out_dir + epi_name
    if not os.path.exists(directory):
      os.makedirs(directory)
    
    print('length of objs ' + str(len(objs)))

    for obj in objs:
      for i in obj['panels']:
        sfx = pathlib.PurePosixPath(obj['filename']).suffix
        x = i[0]
        y = i[1]
        w = i[2]
        h = i[3]
        call(["convert", obj['filename'],"-quality", "100%", "-crop", str(w)+'x'+str(h)+'+'+str(x)+'+'+str(y), out_dir + epi_name +'/'+epi_name +'-'+ '%03d'%inum + sfx ])
        #call(["jpegtran","-crop","-perfect",  str(w)+'x'+str(h)+'+'+str(x)+'+'+str(y), "-outfile", out_dir + str(episode)+'/'+epi_name +'_'+ str(inum)+'.jpg', obj['filename'] ])
        inum+=1

def main():
  print('image preprocessing..(resizing)')
  pre_cutter()
  print('detect scenes boxes..')
  run_kumiko() # TODO : auto split cutting with specific size. = done.
  print('scene box cutting..')
  run_cutter() # TODO : Nothing.

if __name__ == '__main__':
  main()

