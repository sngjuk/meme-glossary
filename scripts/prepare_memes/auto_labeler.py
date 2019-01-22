#!/usr/bin/env python3
'''
Label image with Google Cloud Vision API.
Before use it, check "vision_api_test.sh" in google-vision-setting directory. cred.json is required.
Usage : ./auto_labler.py --meme_dir=./meme_cut/ --output_dir=./output_xml/
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

from google.cloud import vision
from google.cloud.vision import types

def get_args_parser():
  parser = argparse.ArgumentParser(description='Directories for processing')
  parser.add_argument('-i','--meme_dir', type=str, required=True, help='Directory of a input memes.')
  parser.add_argument('-o','--output_dir', type=str, required=True, help='Directory of a output xml.')
  parser.add_argument('--lang_hint', type=str, required=True,
                      help="""Google vision detect language hint. =ko for Korean, 
                      =en English =ja Japanese =zh* Chinese
                      https://cloud.google.com/vision/docs/languages""")
  parser.add_argument('-w','--overwrite', default=False, help='Overwrite xml.')

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()
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
  
  episodes = os.listdir(in_dir)
  episodes.sort()
  # iterate meme dir.
  for episode in episodes:
    images = os.listdir(in_dir+'/'+episode) 

    # xml episode folders should not have whitespace in name.
    xml_ep = episode.replace(' ', '_')
    if not os.path.exists(out_dir+'/'+ xml_ep):
      os.makedirs(out_dir + '/' + xml_ep)
    if episode == '.ipynb_checkpoints':
      continue
    print('\n## Episode : ', episode)
   
    images.sort()    
    for image in images:
      img_path = in_dir + episode + '/' + image
      if not img_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

      x_path  = out_dir + xml_ep +'/' + image
      pre, ext = os.path.splitext(x_path)
      x_path = pre + '.xml'
      xml_file = Path(x_path)
      if xml_file.exists() and not overwrite_flag:
        print('xml already exist : %s ' %(x_path.rsplit('/',1)[1]))
        continue

      print('Label -> %s ' %(image))
      with open(x_path, 'w') as f:
        res_txt = detect_text(img_path, hint)
        if hint == 'ko':
          res_txt = re.sub(r'[^가-힣\s]', '', res_txt)
        elif hint == 'en':
          res_txt = re.sub(r'[^A-z\s]', '', res_txt)

        res_txt = re.sub(r'\t{1,}', ' ', res_txt)
        res_txt = re.sub(r'\n{1,}', ' ', res_txt)
        res_txt = re.sub(r'\s{1,}', ' ', res_txt)
        res_txt = re.search(r'\s{0,}(.*)', res_txt).group(1)
        print(': ' +res_txt)
        s = '{"annotation" : {"folder" : "'+ episode +'", "filename" : "'+ image +'", "segmented": 0, "object" : {"name" : "'+ res_txt +'", "pose" : "Unspecified", "truncated" : 0, "occluded" : 0, "difficult" : 0, "vector" : 0} }}'
        j = json.loads(s)
        f.write(json2xml(j))
        f.close()
      print('saved.')

def main():
  args = get_args_parser()
  print('## Start text detection, using google cloud vision..')
  try :
    run_tagger(args) # xml
    print('\nLabeling & Generate .xml done.')    
    print('overwrite mode : %s' %(args.overwrite))  
    print('GCP detect language : %s\n' %(args.lang_hint))
  except Exception as e:
    print(e)
    print('\nAuto detction failed, check out links below.')  
    print('https://cloud.google.com/vision/docs/libraries')
    print('https://cloud.google.com/vision/docs/detecting-text\n')
    sys.exit()
    
if __name__ == '__main__':
  main()
