#!/usr/bin/env python3
'''
This script is for image cutting from naver webtoon. (rect boxed toon is recommended)
Usage example : ./cutter.py -kumiko_path=kumiko/ -input_path=input_original/ -output_path=output_cut/
sngjuk@gmail.com
'''
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

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-kumiko_path', type=str, default='./', help='directory of kumiko')
  parser.add_argument('-input_path', type=str, required=True,help='directory of a input toon(to be cut) path.')
  parser.add_argument('-output_path', type=str, required=True, help='directory of a output cut path.')
  args = parser.parse_args()

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()
  return args

def resize_img(im, episode, in_dir):
  for h in range(0, im.height, 2200):
    nim = im.crop((0, h, im.width-1, min(im.height, h+2500)-1))
    num = '%05d' % h
    nim.save(in_dir+episode+'/'+"PartialImage-" + num + ".jpg")
    #display(Image('PartialImage-' +str(h) + '.jpg', width=300, height=300))
    #print('----')

#resize file for kumiko. maximum 2500 pix
def pre_cutter(args):
  in_dir = args.input_path

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
      with open(in_dir+episode+'/'+img,"rb") as fp:
        im = PIL.Image.open(fp)
        if im.height > 2500:
          resize_img(im, episode, in_dir)
          os.remove(in_dir+episode+'/'+img)

def run_kumiko(args):
  in_dir = args.input_path
  km_dir = args.kumiko_path

  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode)
    delist = [x for x in imgs if not x.lower().endswith(('.jpg','.jpeg','.png'))]
    print('delete non image files(.jpg, .jpeg, .png) : ' +str(delist))
    for i in delist:
      os.remove(in_dir+str(episode)+'/'+i)

    proc = subprocess.Popen([str(km_dir)+'kumiko', '-i', str(in_dir)
                             +''+str(episode), '-o', str(in_dir)+str(episode)
                             +'/kumiko_res.json'], stdout=subprocess.PIPE)
    output = proc.stdout.read()
    
def run_cutter(args):  
  in_dir = args.input_path
  out_dir = args.output_path

  episodes = os.listdir(in_dir)
  ep_num = 0
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  
  for idx, episode in enumerate(episodes):
    f = open(str(in_dir)+str(episode)+'/kumiko_res.json')
    json_string = f.read()
    f.close()
    
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
        call(["convert", obj['filename'],"-quality", "100%", "-crop", 
              str(w)+'x'+str(h)+'+'+str(x)+'+'+str(y), 
              out_dir + epi_name +'/'+epi_name +'-'+ '%03d'%inum + sfx ])
        inum+=1

def main(args):
  print('image preprocessing..(resizing)')
  pre_cutter(args)
  print('detect scenes boxes..')
  run_kumiko(args) # TODO : auto split cutting with specific size. = done.
  print('scene box cutting..')
  run_cutter(args) # TODO : Nothing.

if __name__ == "__main__":
  args = get_args_parser()
  print(args)
  main(args)
