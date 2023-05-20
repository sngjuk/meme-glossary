#!/usr/bin/env python3
'''
Comics cutting. (rect boxed toon is recommended)
Usage : ./cutter.py --kumiko_path=./kumiko/ --input=./input_original/ --output=./output_cut/
'''
import argparse
import json
import os
import pathlib
import subprocess
import sys
from subprocess import call

import PIL.Image


def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-k', '--kumiko_path', type=str, default='./kumiko/', help='kumiko path')
  parser.add_argument('-i', '--input', type=str, default='./downloaded')
  parser.add_argument('-o', '--output', type=str, default='./cut')
  args = parser.parse_args()  
  return args


def resize_img(im, episode, in_dir):
  for h in range(0, im.height, 2200):
    nim = im.crop((0, h, im.width-1, min(im.height, h+2500)-1))
    num = '%05d' % h
    nim.save(in_dir+episode+'/'+"PartialImage-" + num + ".jpg")
    #display(Image('PartialImage-' +str(h) + '.jpg', width=300, height=300))


# resize img for kumiko. max size is 2500px
def pre_cutter(args):
  in_dir = os.path.abspath(args.input)+ '/'

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
  in_dir = os.path.abspath(args.input) + '/'
  km_dir = os.path.abspath(args.kumiko_path) + '/'

  plist = []
  episodes = os.listdir(in_dir)
  for episode in episodes:
    print(episode)
    imgs = os.listdir(in_dir+episode)
    delist = [x for x in imgs if not x.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print('deleted non image files(.jpg, .jpeg, .png) : ' + str(delist))
    for i in delist:
      call(["rm", "-rf", str(in_dir+str(episode)+'/'+i)])

    p = subprocess.Popen([str(km_dir)+'kumiko', '-i', str(in_dir) + str(episode),
                         '-o', str(in_dir)+str(episode) + '/kumiko_res.json'], stdout=subprocess.PIPE)
    plist.append(p)

  print('wait for subprocess to finish...')
  exit_code = [p.wait() for p in plist]
  print(exit_code)


def run_cutter(args):  
  in_dir = os.path.abspath(args.input) + '/'
  out_dir = os.path.abspath(args.output) + '/'

  episodes = os.listdir(in_dir)
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)

  for idx, episode in enumerate(episodes):
    episode_path = str(in_dir)+str(episode)
    f = open(episode_path + '/kumiko_res.json')
    json_string = f.read()
    f.close()

    objs = json.loads(json_string)
    inum=0

    epi_name = episode.replace(' ', '_').replace('-','_')
    print('Current episode : ' + str(epi_name))

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
        p = call(["convert", obj['filename'], "-quality", "100%", "-crop",
                 str(w)+'x'+str(h)+'+'+str(x)+'+'+str(y),
                 out_dir + epi_name + '/' +epi_name +'-'+ '%03d'%inum + sfx ])
        inum+=1


def main(args):
  print("""\n[Warning] This script may Slice images into pieces and Delete non-image files in directory. 
  (supported type: .jpg .jpeg .png) \n Make sure you're using copy of original folder.""")
  print('Are you sure to continue ? (y/n) : ', end='')
  ans = input()
  if not ans == 'y':
    print('Aborted !')
    sys.exit()
  
  print('\n## Phase 1: Image preprocessing...(resizing)\n')
  pre_cutter(args)
  print('\n## Phase 2: Detect scenes boxes...\n')
  run_kumiko(args)
  print('\n## Cut box slicing with kumiko_res.json...')
  run_cutter(args)
  print('Cutting done.\n')


if __name__ == "__main__":
  args = get_args_parser()
  main(args)
