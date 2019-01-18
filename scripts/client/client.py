import sys
import threading
import zmq
import json

class MgClient:
    def __init__(self, ip='localhost', port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect('tcp://%s:%d' % (ip, port))
        self.port = port
        self.ip = ip
        
    def req_json(self, req_name, query_list, max_img, min_sim):
        x = {
              "req_name" : req_name,
              "queries": query_list,
              "max_image_num": max_img,
              "min_similarity" : min_sim
        }
        return x

    def dank(self, query_list, max_img=10, min_sim=0.10):
        if query_list:
            x = self.req_json('dank', query_list, max_img, min_sim)
            self.socket.send_string(json.dumps(x))
            data = self.socket.recv_string()
            return json.loads(data)
        else :
            return None

    def random(self):
        x = self.req_json('random', None, None, None)
        self.socket.send_string(json.dumps(x))
        data = self.socket.recv_string()
        return json.loads(data)
    
    def close(self):
        """
            Gently close all connections of the client. If you are using BertClient as context manager,
            then this is not necessary.
        """
        self.socket.close()
        self.context.term()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()
        
    def __del__(self):
        self.close()