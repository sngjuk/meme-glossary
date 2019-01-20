#!/usr/bin/env python3
'''
Label image.(vertical rect boxed toon is only available for now.)
Usage : ./manual_labeler.py --meme_dir=./meme_cut/ --output_dir=./output_xml/
sngjuk@gmail.com
'''
import sys
from subprocess import call
import subprocess
import json
import argparse
import io
import os
import re
from pathlib import Path

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-i','--meme_dir', type=str, required=True, help='Directory of a input images.')
  parser.add_argument('-o','--output_dir', type=str, required=True, help='Directory of a output xml.')
  parser.add_argument('-w','--overwrite', default=False, help='Overwrite xml.')
  parser.add_argument('-e', '--auto_empty_label', default=False, help='Label with empty sentence automatically.')
  args = parser.parse_args()

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()
  return args

def json2xml(json_obj, line_padding=""):
  result_list = list()
  json_obj_type = type(json_obj)

  if json_obj_type is list:
    for sub_elem in json_obj:
      result_list.append(json2xml(sub_elem, line_padding))

    return "\n".join(result_list)

  if json_obj_type is dict:
    for tag_name in json_obj:
      sub_obj = json_obj[tag_name]
      result_list.append("%s<%s>" % (line_padding, tag_name))
      result_list.append(json2xml(sub_obj, "\t" + line_padding))
      result_list.append("%s</%s>" % (line_padding, tag_name))
    return "\n".join(result_list)
  return "%s%s" % (line_padding, json_obj)

def run_tagger(args):
  in_dir = os.path.abspath(args.meme_dir) + '/'
  out_dir = os.path.abspath(args.output_dir) + '/'
  overwrite_flag = args.overwrite
  auto_flag = args.auto_empty_label

  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  
  cut_episodes = os.listdir(in_dir)
  cut_episodes.sort()

  for episode in cut_episodes:
    images = os.listdir(str(in_dir)+'/'+str(episode))
    epi_name = episode.replace(' ', '_').replace('-','_')
    if not os.path.exists(out_dir+'/'+str(episode)):
      os.makedirs(str(out_dir) + '/'+epi_name)
    if episode == '.ipynb_checkpoints':
      continue
    print(episode)
    
    images.sort()
    for image in images:
      path = str(in_dir)+str(episode)+'/'+str(image)
      rel_path = str(episode)+'/'+str(image)
      if not path.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

      x_path  = str(out_dir)+epi_name +'/'+str(image).split('.')[0] +'.xml'
      xml_file = Path(x_path)
      if xml_file.exists() and not overwrite_flag:
        print('xml already exist : %s ' %(epi_name+'/'+image))
        continue

      print('Input label for %s : ' %(epi_name+'/'+str(image)) , end='')
      res_txt = ''
      if not auto_flag:
        try:
          res_txt = input()
        except KeyboardInterrupt:
          print('\n## Labeling cancled! : %s ' %(rel_path))
          sys.exit()
      else:
        print('Auto empty labeling')

      print('Label : ',res_txt)

      with open(x_path, 'w') as f:
        s = '{"annotation" : {"folder" : "'+str(episode)+'", "filename" : "'+ rel_path +'", "segmented": 0, "object" : {"name" : "'+str(res_txt)+'", "pose" : "Unspecified", "truncated" : 0, "occluded" : 0, "difficult" : 0, "vector" : 0} }}'
        j = json.loads(s)
        f.write(json2xml(j))
        f.close()
      print('Created :', rel_path)

def main():
  args = get_args_parser()
  run_tagger(args) # xml
  print('xml generation done.')
  print('overwrite mode : %s' %(args.overwrite))

if __name__ == '__main__':
  main()
