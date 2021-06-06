#!/usr/bin/env python3
"""
Generate .vec voca file from image xml folder. (voca format is KeyedVectors.load_word2vec_format.) [filename : vector]
Usage : ./2_embed_labes.py --model_path=./model.bin --xml_dir=./xml_dir/
"""

import sys
import os
import re
import argparse
import pickle
import numpy as np
from lxml import objectify


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


# requires : sentence embedding -- input : model_bin, xml_folder, vec_out_dir
def get_args_parser():
    parser = argparse.ArgumentParser(description='Paths for processing')
    parser.add_argument('-m', '--model_path', type=str, default='./model.bin',
                        required=True, help='Path of model.')
    parser.add_argument('-i', '--xml_dir', type=str, required=True,
                        help='Directory of xml labels. e.g ./4_label_xml/')
    parser.add_argument('-o', '--saved_embedding', type=str, default='saved_embedding.pickle',
                        help='Path of output .vec file. e.g ./5_saved_embedding.pickle')
    parser.add_argument('-mt', '--model_type', type=str, default='sent2vec', 
                        help="Embedding model (\"tf\" or \"sent2vec\")")
    parser.add_argument('-l', '--lang', default=None,
                        help='for additional tokenizing only for korean for performance')

    args = parser.parse_args()
    return args

def refine_text(text):
    text = text.replace('\t', ' ').replace('\n', ' ').replace('\s+', ' ')
    text = re.search(r'\s*(.*)', text).group(1)
    text = re.sub(r'\s+$', '', text)
    return text

def xml2vec(args):
    model_path = os.path.abspath(args.model_path)
    xml_dir = os.path.abspath(args.xml_dir)
    out_path = os.path.abspath(args.saved_embedding)
    print('\nmodel path : ', model_path)
    print(xml_dir)
    print(out_path)

    model = None
    if args.model_type == 'tf':
        from server.nlp.TensorflowModel import TensorflowModel
        model = TensorflowModel(args.lang)
    elif args.model_type == 'sent2vec':
        from server.nlp.Sent2VecModel import Sent2VecModel
        model = Sent2VecModel(args.lang)

    print('loading model... ')
    model.load_model(model_path)

    num_word = 0
    vec_size = None

    # Writing to .vec file.
    vecfile_content = ''
    episodes = os.listdir(xml_dir)
    episodes.sort()

    # batched restuls
    list_of_file_path = []
    list_of_text = []
    list_of_embedding = []
    embedding_dimension = 0

    for episode in episodes:
        epi_dir = os.path.join(xml_dir, episode)
        if not os.path.isdir(epi_dir):
            continue

        print('\n## Episode : ', episode)
        tagged_xmls = os.listdir(os.path.join(xml_dir, episode))
        tagged_xmls.sort()

        for tagged_xml in tagged_xmls:
            tagged_xml_path = os.path.join(epi_dir, tagged_xml)
            # TODO: check if it's relative path
            rel_path = os.path.join(episode, tagged_xml)

            if not tagged_xml_path.lower().endswith('.xml'):
                continue

            # open .xml
            with open(tagged_xml_path) as f:
                xml_string = f.read()
                if not xml_string:
                    continue

                xml_root = objectify.fromstring(xml_string)

                # Embedding text is in xml['object']['name']
                m_text = refine_text(str(xml_root['object']['name']))
                embedding = model.embed_sentence(m_text)
                reshaped_embedding = embedding.reshape(-1)

                list_of_text.append(m_text)
                list_of_embedding.append(reshaped_embedding)               
                embedding_dimension = len(reshaped_embedding)

                image_file_name = refine_text(str(xml_root['filename']))
                list_of_file_path.append(os.path.join(episode, image_file_name))
                print(str(tagged_xml) + ' ' + str(m_text))
    
    # embedding shape - (total_file_num, 1, vector_size)
    print('Save to pickle..')
    saved_dict = {}
    saved_dict['text']      = list_of_text
    saved_dict['embedding'] = np.array(list_of_embedding)
    saved_dict['embedding_dimension'] = embedding_dimension
    saved_dict['file_path'] = list_of_file_path

    pickle.dump(saved_dict, open(out_path, 'wb'))

    
def main():
    args = get_args_parser()
    xml2vec(args)
    print('Write done : %s\n' % args.saved_embedding)


if __name__ == "__main__":
    main()
