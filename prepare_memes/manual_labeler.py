#!/usr/bin/env python3
'''
Label image.
Usage : ./manual_labeler.py --meme_dir=./meme_cut/ --output_dir=./output_xml/
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
from lxml import objectify

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-i','--meme_dir', type=str, required=True, help='Directory of a input images.')
  parser.add_argument('-o','--output_dir', type=str, required=True, help='Directory of a output xml.')
  parser.add_argument('-w','--overwrite', default=False, help='Overwrite xml.')
  parser.add_argument('-e', '--auto_empty_label', default=False, help='Label with empty sentence automatically.')

  args = parser.parse_args()
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

def rm_gbg_from_xml(value):
  value = str(value).replace('\t','').replace('\n','')
  value = re.search(r'\s{0,}(.*)', value).group(1)
  return value

def run_tagger(args):
  in_dir = os.path.abspath(args.meme_dir) + '/'
  out_dir = os.path.abspath(args.output_dir) + '/'
  overwrite_flag = args.overwrite
  auto_flag = args.auto_empty_label

  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  
  episodes = os.listdir(in_dir)
  episodes.sort()
  # iterate meme dir.
  for episode in episodes:
    # xml episode folders should not have whitespace in name.        
    images = os.listdir(str(in_dir)+'/'+str(episode))
    epi_name = episode.replace(' ', '_')
    
    if not os.path.exists(out_dir+'/'+epi_name):
      os.makedirs(out_dir +'/'+epi_name)
    if episode == '.ipynb_checkpoints':
      continue
    print('\n## Episode : ',episode)
    
    images.sort()
    for image in images:
      path = in_dir +episode+ '/' +image
      if not path.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

      x_path  = out_dir + epi_name +'/'+ image
      pre, ext = os.path.splitext(x_path)
      x_path = pre + '.xml'
      xml_file = Path(x_path)
      ori_txt = ''
      if xml_file.exists():
        if not overwrite_flag:
          print('xml already exist : %s ' %( x_path.rsplit('/',1)[1]))
          continue
        else :
          with open(x_path,'r') as f:
            xml_str = f.read()
            if xml_str:
              xml_root = objectify.fromstring(xml_str)
              ori_txt = rm_gbg_from_xml(xml_root['object']['name'])

      print('Label -> %s, \noriginal label : [%s]\n: ' %(image, ori_txt) , end='')
      res_txt = None

      if not auto_flag:
        try:
          res_txt = input()
          if res_txt == '0':
            print('skipped.')
            continue

          elif res_txt == '9':
            print('episode skipped.')
            break

          res_txt = re.sub(r'\t{1,}', ' ', res_txt)
          res_txt = re.sub(r'\n{1,}', ' ', res_txt)
          res_txt = re.sub(r'\s{1,}', ' ', res_txt)
          res_txt = re.search(r'\s{0,}(.*)', res_txt).group(1)

        except KeyboardInterrupt:
          print('\n## Cancled : %s ' %(epi_name+'/' +x_path.rsplit('/',1)[1]))
          sys.exit()
      else:
        print('Auto empty labeling')
        
      print('label :[%s] ' %(res_txt), end='')

      with open(x_path, 'w') as f:
        s = '{"annotation" : {"folder" : "'+ episode +'", "filename" : "'+ image +'", "segmented": 0, "object" : {"name" : "'+res_txt+'", "pose" : "Unspecified", "truncated" : 0, "occluded" : 0, "difficult" : 0, "vector" : 0} }}'
        j = json.loads(s)
        f.write(json2xml(j))
        f.close()
      print('saved.')

def main():

  print("\n# Manual labeler \n\n Input '0' to skip label.") 
  print("       '9' to skip episode.\n Ctrl+c to cancel.")
  args = get_args_parser()
  run_tagger(args) # xml
  print('\nLabeling done.')
  print('overwrite mode : %s' %(args.overwrite))  
  print('Labeling & Generate .xml done.\n')

if __name__ == '__main__':
  main()
