import sys
import threading
import zmq
import json
import base64
import re

class MgClient:
    def __init__(self, ip='localhost', port=5555):
        self.ip = ip
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)        
        self.socket.connect('tcp://%s:%d' % (self.ip, self.port))

    def req_json(self, req_name, query_list, max_img, min_sim):
        """
        server_rep_msg = {
            "rep": rep_name,                    # str
            "query": query,                     # str
            "oov" : oov_flag,                   # bool
            "result_exist": result_exist_flag,  # bool
            "memefname": memefname_list,        # list
            "episode": episode_list,              
            "text" : text_list,
            "imgdata": imgdata_list,
            "sim": sim_list
        }
        """
        req_json = {
              "req" : req_name,          # str
              "queries": query_list,     # list of str
              "max_image_num": max_img,  # int
              "min_similarity" : min_sim # float
        }
        return req_json

    # base64 encoded, jsoned image : should be unpacked before decode.
    def unpack_b64_from_json(self, unloaded_json):
        for idx, ujson in enumerate(unloaded_json):
          unpacked_data = []
          for data in ujson['imgdata']:
            data = data.replace("'", '"')
            unpacked_b64data = re.search(r'\"(.*)\"', data).group(1)
            unpacked_data.append(unpacked_b64data)
          unloaded_json[idx]['imgdata'] = unpacked_data

        return unloaded_json
    
    # REQ: 1 dank query -> REP: N memes in a json in a list. 
    #     = dank(['req_query']) -> [rep_json([memefname_list, episode_list, imgdata_list, ...])]
    
    # REQ: N dank query -> REP: N jsons in a list. 
    #     = dank(['req1_query', 'req2_query']) -> [rep1_json1(...), rep2_json(...), ...]
    def dank(self, query_list, max_img=10, min_sim=0.10):
        if max_img > 10:
            max_img = 10

        if query_list:
            x = self.req_json('dank', query_list, max_img, min_sim)
            self.socket.send_string(json.dumps(x))
            data = self.socket.recv_string()
            return self.unpack_b64_from_json(json.loads(data))
        else :
            return None
        
    # REQ: 1 random query -> REP: 1 meme in a json in a list. 
    #     = random() -> [ rep_json ]
    def random(self):
        x = self.req_json('random', None, None, None)
        self.socket.send_string(json.dumps(x))
        data = self.socket.recv_string()
        return self.unpack_b64_from_json(json.loads(data))
    
    def save_meme(self, meme_data_base64, path):
        with open(path, 'wb') as f:
            data = base64.b64decode(meme_data_base64)
            f.write(data)
    
    def close(self):
        self.socket.close()
        self.context.term()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()
        
    def __del__(self):
        self.close()
