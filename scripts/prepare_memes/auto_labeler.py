#!/usr/bin/env python3
'''
Label image with Google Cloud Vision API.
Before use it, check "vision_api_test.sh" in google-vision-setting directory. cred.json is required.
Usage : ./auto_labler.py --meme_dir=./meme_cut/ --output_dir=./output_xml/
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
# Imports the Google Cloud client library
from google.cloud import vision
from google.cloud.vision import types

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-i','--meme_dir', type=str, required=True, help='Directory of a input images.')
  parser.add_argument('-o','--output_dir', type=str, required=True, help='Directory of a output xml.')
  parser.add_argument('--lang_hint', type=str, default='ko',
                      help="""Google vision detect language hint. Default is -Korean. 
                      https://cloud.google.com/vision/docs/languages""")
  parser.add_argument('-w','--overwrite', default=False, help='Overwrite xml.')
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

def detect_text(path, hint):
  """Detects text in the file."""
  client = vision.ImageAnnotatorClient()

  with io.open(path, 'rb') as image_file:
    content = image_file.read()
    image_file.close()

  image = vision.types.Image(content=content)
  img_ctxt = vision.types.ImageContext()
  img_ctxt.language_hints.append(hint)

  response = client.text_detection(image=image, image_context=img_ctxt)
  texts = response.text_annotations

  res = ''
  for text in texts:
    res = '"{}"'.format(text.description)
    break

  return res

def run_tagger(args):
  in_dir = os.path.abspath(args.meme_dir)+ '/'
  out_dir = os.path.abspath(args.output_dir)+ '/'
  hint = args.lang_hint
  overwrite_flag = args.overwrite

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

      with open(x_path, 'w') as f:
        res_txt = detect_text(path, hint)
        res_txt = re.sub(r'[^가-힣\s]', '', res_txt)
        res_txt = re.sub(r'\t{1,}', ' ', res_txt)
        res_txt = re.sub(r'\n{1,}', ' ', res_txt)
        res_txt = re.sub(r'\s{1,}', ' ', res_txt)
        res_txt = re.search(r'\s{0,}(.*)', res_txt).group(1)
        print('Texts: ' +str(res_txt))
        s = '{"annotation" : {"folder" : "'+str(episode)+'", "filename" : "'+ rel_path +'", "segmented": 0, "object" : {"name" : "'+str(res_txt)+'", "pose" : "Unspecified", "truncated" : 0, "occluded" : 0, "difficult" : 0, "vector" : 0} }}'
        j = json.loads(s)
        f.write(json2xml(j))
        f.close()
      print('Created :', x_path)

def main():
  args = get_args_parser()
  print('tagging using google vision..')
  run_tagger(args) # xml
  print('tagging & generate .xml done.')
  print('overwrite mode : %s' %(args.overwrite))  

if __name__ == '__main__':
  main()
