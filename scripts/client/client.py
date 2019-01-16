#!/usr/bin/env python3

import sys
import threading
import time
import uuid
import warnings
from collections import namedtuple
import re

import numpy as np
import zmq
import json
from IPython.display import display, HTML

class MgClient:
    def __init__(self, ip='localhost', port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect('tcp://%s:%d' % (ip, port))
        self.port = port
        self.ip = ip

    def close(self):
        """
            Gently close all connections of the client. If you are using BertClient as context manager,
            then this is not necessary.
        """
        self.socket.close()
        self.context.term()

    def dank(self, query_list, img_num=10, sim=0.10):
        if query_list:
            x = {
              "queries": query_list,
              "max_image_num": img_num,
              "min_similarity" : sim
            }
            self.socket.send_string(json.dumps(x))
            data = self.socket.recv_string()
            return json.loads(data)
            
        else :
            return None

    def show_result(self, unloaded_json):
        for y in unloaded_json:
    #        y = json.loads(y)
            if y['find_success'] == False:
                print('====dont know that word TT')
                continue

            for filename in y['memes']:
                decoded = y['memes'][filename].replace("'", '"')
                decoded = re.search(r'\"(.*)\"', decoded).group(1)
                display(HTML('''<img src="data:image/png;base64,''' + decoded + '''">'''))    
                print(y['texts'][filename])
                print(y['sims'][filename])
            print("--- done ---")

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()
        
    def __del__(self):
        self.close()