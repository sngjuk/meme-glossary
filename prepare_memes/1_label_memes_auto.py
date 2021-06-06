#!/usr/bin/env python3

"""
Label image with Google Cloud Vision API.
Before use it, please test google vision in "google-vision-setting" folder. credential json file is required.
Ref: https://codelabs.developers.google.com/codelabs/cloud-vision-api-python#0

Usage :
1. export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)"/google_vision_test/cred.json"
2. ./1_label_memes_auto.py -i input_comics_episodes_dir -o output_tagged --lang_hint=ko

*comics_episodes_dir: folder of image folders
"""

import sys
import json
import argparse
import io
import os
import re
import PIL.Image
from pathlib import Path
from google.cloud import vision


def get_args_parser():
    parser = argparse.ArgumentParser(description='Directories for labeling')
    parser.add_argument('-i', '--meme_dir', type=str, required=True, 
                        help='Directory of input meme directories')
    parser.add_argument('-o', '--output_dir', type=str, default='tagged_xml', 
                        help='Folder directory of output xml folders.')
    parser.add_argument('--lang_hint', type=str, required=True,
                        help="""Google vision detect language hint. =ko for Korean, 
                        =en English =ja Japanese =zh* Chinese
                        https://cloud.google.com/vision/docs/languages""")
    parser.add_argument('-w', '--overwrite', default=False, help='Overwrite xml.')

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

    image = vision.Image(content=content)

    img_context = vision.ImageContext()
    img_context.language_hints.append(hint)

    response = client.text_detection(image=image, image_context=img_context)
    texts = response.text_annotations 

    res = ''
    for text in texts:
        res = '"{}"'.format(text.description)
        break
        
    return res


def run_tagger(args):
    in_dir = os.path.abspath(args.meme_dir)
    out_dir = os.path.abspath(args.output_dir)
    hint = args.lang_hint
    overwrite_flag = args.overwrite

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    episodes = os.listdir(in_dir)
    episodes.sort()

    # iterate meme dir.
    for episode in episodes:
        epi_dir = os.path.join(in_dir, episode)
        if not os.path.isdir(epi_dir):
            continue

        print('\n## Episode : ', episode)

        # xml episode folders should not have whitespace in name.
        xml_ep = episode.replace(' ', '_')
        xml_path = os.path.join(out_dir, xml_ep)

        if not os.path.exists(xml_path):
            os.makedirs(xml_path)

        images = os.listdir(epi_dir)
        images.sort()

        for image_file_name in images:
            # check if it's image file by file extension
            if not image_file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                continue

            img_path = os.path.join(in_dir, episode, image_file_name)
            print(image_file_name)

            x_path = os.path.join(out_dir, xml_ep, image_file_name)
            pre, ext = os.path.splitext(x_path)
            x_path = pre + '.xml'

            if Path(x_path).exists() and not overwrite_flag:
                print('xml already exist : %s ' % (x_path.rsplit('/', 1)[1]))
                continue

            with open(x_path, 'w') as xml_file, PIL.Image.open(img_path) as pil_image:
                res_txt = detect_text(img_path, hint)

                if hint == 'ko':
                    res_txt = re.sub(r'[^가-힣\s]', '', res_txt)
                elif hint == 'en':
                    res_txt = re.sub(r'[^A-z\s]', '', res_txt)

                res_txt = re.sub(r'\t+', ' ', res_txt)
                res_txt = re.sub(r'\n+', ' ', res_txt)
                res_txt = re.sub(r'\s+', ' ', res_txt)
                res_txt = re.search(r'\s*(.*)', res_txt).group(1)
                print(': ' + res_txt)

                pil_width, pil_height = pil_image.size
                pil_depth = len(pil_image.getbands())

                s = '{"annotation" : {"folder" : "' + episode + '", "filename" : "' + image_file_name + \
                    '", "size" : {"width" : "' + str(pil_width) + '", "height" : "' + str(pil_height) + \
                    '", "depth" : "' + str(pil_depth) + '"}, "object" : {"name" : "' + res_txt + \
                    '", "difficult" : "0"} }}'

                j = json.loads(s)
                xml_file.write(json2xml(j))
                xml_file.close()


def main():
    args = get_args_parser()
    print('## Start text detection, using google cloud vision..')
    try:
        run_tagger(args)  # xml
        print('\nLabeling & Generate .xml done.')
        print('overwrite mode : %s' % args.overwrite)
        print('GCP detect language : %s\n' % args.lang_hint)
    except Exception as e:
        print(e)
        print('\nAuto detection failed, check out links below.')
        print('https://cloud.google.com/vision/docs/libraries')
        print('https://cloud.google.com/vision/docs/detecting-text\n')
        sys.exit()


if __name__ == '__main__':
    main()
