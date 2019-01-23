"""
Serve 'dank', 'random' request from MgClient with ZMQ.
"""
import os
from gensim.models import KeyedVectors
import numpy as np
from collections import OrderedDict
import re
from random import randint
import random
from lxml import objectify

import base64
import json

import threading
import zmq
from .helper import set_logger
from .nlp.model import EmbedModel

class MgServer(threading.Thread):
    def __init__(self, args):
        super().__init__()
        """Server routine"""
        self.logger = set_logger('VENTILATOR')
        self.model_path = os.path.abspath(args.model_path)
        self.meme_dir = os.path.abspath(args.meme_dir)+'/'
        self.xml_dir = os.path.abspath(args.xml_dir)+'/'
        self.vec_path = os.path.abspath(args.vec_path)
        self.port = args.port
        self.thread_num = args.thread_num
        
        self.url_worker = "inproc://workers"
        self.url_client = "tcp://*:" + self.port
        self.logger.info('opend server : %s' %(self.url_client))
        self.logger.info('num of threads : %s' %(self.thread_num))
        
        # Load model
        self.logger.info('loading model...')
        self.model = EmbedModel()
        self.model.load_model(self.model_path)
        self.word_vector = KeyedVectors.load_word2vec_format(self.vec_path)
        self.logger.info('model load done.')
        random.seed()
        
        # Prepare Context and Sockets
        self.logger.info('Prepare Context and Sockets...')
        self.context = zmq.Context.instance()

        # Socket to talk to clients
        self.logger.info('opening client socket...')
        self.clients = self.context.socket(zmq.ROUTER)
        self.clients.bind(self.url_client)

        # Socket to talk to workers
        self.logger.info('opening worker socket...')        
        self.workers = self.context.socket(zmq.DEALER)
        self.workers.bind(self.url_worker)
        
    def run(self):
        # Launch pool of worker threads
        self.logger.info('starting workers...')
        self.threads = []
        for i in range(self.thread_num):
            #thread = threading.Thread(target=worker_routine, args=(url_worker,i,))
            thread = MgServer.MgWorker(worker_url=self.url_worker, worker_id=i, model=self.model,
                                       meme_dir=self.meme_dir, xml_dir=self.xml_dir, vector=self.word_vector)
            thread.start()
            self.threads.append(thread)

        zmq.proxy(self.clients, self.workers)
    
    def close(self):
        self.logger.info('shutting down...')
        for p in self.threads:
            p.close()
            print(p, ': thread down.')
        self.join()
        
    def __exit__(self):
        self.close()

    class MgWorker(threading.Thread):
        def __init__(self, worker_url, worker_id, model, meme_dir, xml_dir, vector, context=None):
            super().__init__()
            self.logger = set_logger('WORKER-%d ' % worker_id)
            self.worker_url = worker_url
            self.worker_id = worker_id
            self.model = model
            self.meme_dir = meme_dir
            self.xml_dir = xml_dir
            self.vector = vector
            self.context = context
            self.meme_list = self.vector.index2entity
            
        def rep_json(self, rep_name, query, oov_flag, result_exist_flag, memefname_list, episode_list, text_list, 
                     imgdata_list, sim_list):
            
            rep_json = {
              "rep": rep_name,
              "query": query,
              "oov" : oov_flag,
              "result_exist": result_exist_flag,
              "memefname": memefname_list,
              "episode": episode_list,                
              "text" : text_list,
              "imgdata": imgdata_list,
              "sim": sim_list
            }
            return rep_json
        
        def rm_gbg_from_xml(self, value):
            # objectify.fromstring() returns value with garbage.
            value = str(value).replace('\t','').replace('\n','')
            value = re.search(r'\s{0,}(.*)', value).group(1)
            return value
        
        def get_text_and_bytes(self, xml_file_name):
            meme_fname = None
            episode = None            
            text = None
            data = None
            # xml_file_name : episode/some.xml
            xml_path = self.xml_dir + xml_file_name
            with open(xml_path) as xml_file:
                xml_str = xml_file.read()
                xml_root = objectify.fromstring(xml_str)
                # ['filename'] : some.jpg
                # .xml contains info of image file.
                meme_fname = self.rm_gbg_from_xml(xml_root['filename'])
                episode = self.rm_gbg_from_xml(xml_root['folder'])            
                text = self.rm_gbg_from_xml(xml_root['object']['name'])       
                
                meme_path = self.meme_dir + episode +'/'+ meme_fname
                with open(meme_path, 'rb') as meme_file:
                    # Encode image with base64 and str.
                    data = base64.b64encode(meme_file.read())
                    data = str(data)

            return meme_fname, episode, text, data

        def image_result_json(self, query, request):
            max_image_num = request['max_image_num']
            min_similarity = request['min_similarity']
            
            """
            memefname_list[ meme1_filename, meme2_filename, ... ]
            episode_list[ meme1_episode, meme2_episode ... ]  
            text_list[ meme1_text,  meme2_text ... ]            
            imgdata_list[ meme1_base64data,  meme2_base64data,  ... ]
            sim_list[ meme1_similarity, meme2_similarity, ... ]
            """
            memefname_list = []
            episode_list = []           
            text_list = []
            imgdata_list = []
            sim_list = []
            oov_flag = True
            result_exist_flag = False

            query_vector = self.model.embed_sentence(query)
            
            if(np.any(query_vector[0])):
                oov_flag = False
                query_vector = np.array(query_vector[0], dtype=np.float32)
                most_sim_vectors = self.vector.similar_by_vector(query_vector)
                
                for img_num, xmlfname_and_similarity in enumerate(most_sim_vectors):
                    # xmlfname_and_similarity [0] : xml fname, [1] : similarity.
                    if img_num >= max_image_num:
                        break
                    if xmlfname_and_similarity[1] < min_similarity:
                        break

                    meme_fname, episode, text, data = self.get_text_and_bytes(xmlfname_and_similarity[0])

                    memefname_list.append(meme_fname)
                    episode_list.append(episode)                    
                    text_list.append(text)
                    imgdata_list.append(data)
                    sim_list.append(xmlfname_and_similarity[1])

                if(len(imgdata_list)):
                    result_exist_flag = True

            return self.rep_json(request['req'], query, oov_flag, result_exist_flag, 
                                 memefname_list, episode_list, text_list, imgdata_list, sim_list)
            
        def dank_dealer(self, request):
            """
            Send back multiple memes.
            # REQ: 1 dank query. -> REP: N memes in a json in a list. 
            #     = MgClient.dank(['req_query']) -> [rep_json([memefname_list, episode_list, imgdata_list, ...])]

            # REQ: N dank queries. -> REP: N jsons in a list. 
            #     = MgClient.dank(['req1_query', 'req2_query']) -> [rep1_json(...), rep2_json(...), ...]
            """            
            send_back_results = []
            for query in request['queries']:
                # json_dump = json.dumps(self.image_result_json(req))
                rep_json = self.image_result_json(query, request)
                send_back_results.append(rep_json)
            return json.dumps(send_back_results)
            
        def random_dealer(self, request):
            """
            Send back single meme.
            # REQ: 1 random query. -> REP: 1 meme in a json in a list. 
            #     = MgClient.random() -> [rep_json([memefname_list, episode_list, imgdata_list, ...])]
            """
            memefname_list = []
            episode_list = []
            text_list = []
            imgdata_list = []    
            
            send_back_result = []
            ridx = randint(0, len(self.meme_list)-1)

            meme_fname, episode, text, data = self.get_text_and_bytes(self.meme_list[ridx])
            memefname_list.append(meme_fname)
            episode_list.append(episode)                    
            text_list.append(text)
            imgdata_list.append(data)
            
            rep_json = self.rep_json(request['req'], query=None, oov_flag=False, result_exist_flag=True, 
                              memefname_list=memefname_list, episode_list=episode_list, text_list=text_list, 
                              imgdata_list=imgdata_list, sim_list=[])
            send_back_result.append(rep_json)
            
            return json.dumps(send_back_result)
            
        def run(self):
            """Worker routine"""
            self.context = self.context or zmq.Context.instance()
            # Socket to talk to dispatcher
            self.socket = self.context.socket(zmq.REP)
            self.socket.connect(self.worker_url)

            while True:
                self.logger.info('waiting for query worker id %d: ' % (int(self.worker_id)))
                # query  = self.socket.recv().decode("utf-8")
                request = self.socket.recv_string()
                request = json.loads(request)
                
                self.logger.info('request\treq worker id %d: %s %s' % (int(self.worker_id), str(request['req']),
                                                                       str(request['queries'])))
                rep_json = None
                if request['req'] == 'dank':
                    rep_json = self.dank_dealer(request)
                    
                elif request['req'] == 'random':
                    rep_json = self.random_dealer(request)
                
                # response.
                self.socket.send_string(rep_json)
        
        def close(self):
            self.logger.info('shutting %d worker down...' %(self.worker_id))
            self.terminate()
            self.join()
            self.logger.info('%d worker terminated!' %(self.worker_id))
