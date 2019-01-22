#!/usr/bin/env python3
'''
Comics cutting. (rect boxed toon is recommended)
Usage : ./cutter.py --kumiko_dir=./kumiko/ --meme_dir=./input_original/ --out_dir=./output_cut/
'''
import os
import sys
from subprocess import call
import subprocess
import json
import argparse
import re
import PIL.Image
import pathlib

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-k', '--kumiko_dir', type=str, default='./kumiko/', help='Directory of kumiko')
  parser.add_argument('-i', '--meme_dir', type=str, required=True,help='Directory of a input toon(to be cut).')
  parser.add_argument('-o', '--out_dir', type=str, required=True, help='Directory of a output cut.')

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()
  args = parser.parse_args()  
  return args

def resize_img(im, episode, in_dir):
  for h in range(0, im.height, 2200):
    nim = im.crop((0, h, im.width-1, min(im.height, h+2500)-1))
    num = '%05d' % h
    nim.save(in_dir+episode+'/'+"PartialImage-" + num + ".jpg")
    #display(Image('PartialImage-' +str(h) + '.jpg', width=300, height=300))

#resize file for kumiko. maximum 2500 pix
def pre_cutter(args):
  in_dir = os.path.abspath(args.meme_dir)+ '/'

  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode+'/')
    imgs.sort()
    
    for img in imgs:
      if not img.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

      with open(in_dir+episode+'/'+img,"rb") as fp:
        im = PIL.Image.open(fp)
        if im.height > 2500:
          print('current image : %s' % (str(episode+'/'+img)))
          print('image is to big to detect box! (lager then 2500 pix) Resizing executed.')
          print('(it may produce sliced cut, manual filtering is required.)')
          resize_img(im, episode, in_dir)
          os.remove(in_dir+episode+'/'+img)

def run_kumiko(args):
  in_dir = os.path.abspath(args.meme_dir) + '/'
  km_dir = os.path.abspath(args.kumiko_dir)+ '/'

  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode)
    delist = [x for x in imgs if not x.lower().endswith(('.jpg','.jpeg','.png'))]
    print('delete non image files(.jpg, .jpeg, .png) for kumiko module. : ' +str(delist))
    for i in delist:
      call(["rm", "-rf", str(in_dir+str(episode)+'/'+i)])

    proc = subprocess.Popen([str(km_dir)+'kumiko', '-i', str(in_dir)
                             +''+str(episode), '-o', str(in_dir)+str(episode)
                             +'/kumiko_res.json'], stdout=subprocess.PIPE) 
    output = proc.stdout.read()
    
def run_cutter(args):  
  in_dir = os.path.abspath(args.meme_dir)+ '/'
  out_dir = os.path.abspath(args.out_dir)+ '/'

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

    epi_name = episode.replace(' ', '_').replace('-','_')
    print('Current episode : ' +str(epi_name))

    directory = out_dir + epi_name
    if not os.path.exists(directory):
      os.makedirs(directory)
    
    print('num of image files : ' + str(len(objs)))
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
  print("""\n[Warning] This script may Slice images into pieces and Delete non-image files in directory. 
  (supported type: .jpg .jpeg .png) \n Make sure you're using copy of original folder.""")
  print('Are you sure to continue ? (y/n) : ' ,end='')
  ans = input()
  if not ans == 'y':
    print('Aborted !')
    sys.exit()
  
  print('\n## Phase 1: Image preprocessing...(resizing)\n')
  pre_cutter(args)
  print('\n## Phase 2: Detect scenes boxes...\n')
  run_kumiko(args) # TODO : auto split cutting with specific size. = done.
  print('\n## Cut box slicing with kumiko_res.json...')
  run_cutter(args)
  print('Cutting done.\n')

if __name__ == "__main__":
  args = get_args_parser()
  main(args)
