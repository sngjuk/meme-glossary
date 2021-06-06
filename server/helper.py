'''
Author : Han Xiao <artex.xh@gmail.com> <https://hanxiao.github.io>
'''
import argparse
import logging
import os
import sys


__all__ = ['set_logger', 'get_args_parser']

def set_logger(context, verbose=False):
    if os.name == 'nt':  # for Windows
        return NTLogger(context, verbose)

    logger = logging.getLogger(context)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        '%(levelname)-.1s:' + context + ':[%(filename).3s:%(funcName).3s:%(lineno)3d]:%(message)s',
        datefmt='%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(console_handler)
    return logger

def get_args_parser():
    parser = argparse.ArgumentParser(description='arguments for MgServer')

    parser.add_argument('-m','--model_path', type=str, required=True, 
                        help='Path of trained model, e.g ./model.bin')
    parser.add_argument('-mt', '--model_type', type=str, default='sent2vec', 
                        help="Embedding model (\"tf\" or \"sent2vec\")")
    parser.add_argument('-i','--meme_dir', type=str, required=True, 
                        help='Directory of input meme directories e.g image_folder')
    parser.add_argument('-e','--saved_embedding', type=str, required=True, 
                        help='Path of saved embedding .pickle file. e.g saved_embedding.pickle')
    parser.add_argument('-l', '--lang', default=None,
                        help='for additional tokenizing only for korean, for better performance')
    parser.add_argument('-p','--port', type=str, default='5555', help='opening port number')
    parser.add_argument('-t','--thread_num', type=int, default=4, help='number of thread on server.')

    args = parser.parse_args()

    return args