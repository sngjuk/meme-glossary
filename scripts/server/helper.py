'''
Author : Han Xiao <artex.xh@gmail.com> <https://hanxiao.github.io>
'''
import argparse
import logging
import os
import sys
import uuid

import zmq
from zmq.utils import jsonapi

__all__ = ['set_logger', 'get_args_parser']

def set_logger(context, verbose=False):
    if os.name == 'nt':  # for Windows
        return NTLogger(context, verbose)

    logger = logging.getLogger(context)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        '%(levelname)-.1s:' + context + ':[%(filename).3s:%(funcName).3s:%(lineno)3d]:%(message)s', datefmt=
        '%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(console_handler)
    return logger

def get_args_parser():
    parser = argparse.ArgumentParser(description='arguments for MgServer')

    parser.add_argument('-mp','--model_path', type=str, required=True,
                        default='/root/shared_data/model/my_model_lr5_ngram1_epch11.bin',help='directory of trained model')
    parser.add_argument('-vp','--vec_path', type=str, required=True, default='/root/shared_data/embedding/fast_sent.vec',
                        help='directory of a .vec file {filename : vector}')
    parser.add_argument('-xp','--xml_path', type=str, default='',
                        help='directory of a Meme xml file, May be required for page rank in next update.')
    parser.add_argument('-p','--port', type=str, default='5555',
                        help='opening port number')
    parser.add_argument('-t','--thread_num', type=int, default=4,
                        help='number of thread on server.')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    return args
