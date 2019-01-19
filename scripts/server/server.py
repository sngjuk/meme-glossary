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
from server.helper import set_logger
from server.model import EmbedModel

class MgServer(threading.Thread):
    def __init__(self, args):
        super().__init__()
        """Server routine"""
        self.logger = set_logger('VENTILATOR')
        self.model_path = os.path.abspath(args.model_path)
        self.image_dir = os.path.abspath(args.image_dir)+'/'
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
        
        # Prepare our context and sockets
        self.logger.info('Prepare our context and sockets...')
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
                                       image_dir=self.image_dir, vector=self.word_vector)
            thread.start()
            self.threads.append(thread)

        zmq.proxy(self.clients, self.workers)
    
    def close(self):
        self.logger.info('shutting down...')
        for p in self.threads:
            p.close()
        self.join()
        
    def __exit__(self):
        self.close()

    class MgWorker(threading.Thread):
        def __init__(self, worker_url, worker_id, model, image_dir, vector, context=None):
            super().__init__()
            self.logger = set_logger('WORKER-%d ' % worker_id)
            self.worker_url = worker_url
            self.worker_id = worker_id
            self.model = model
            self.vector = vector
            self.context = context
            self.meme_list = self.vector.index2entity
            
        def rep_json(self, query, find_success, meme_dict, epi_dict, text_dict, sim_dict):
            x = {
              "query": query,
              "find_success": find_success,
              "memes": meme_dict,
              "episodes": epi_dict,
              "texts" : text_dict,
              "sims" : sim_dict
            }
            return x

        def get_text_and_bytes(self, xml_file_name):
            text = None
            epis = None
            data = None
            with open(xml_file_name) as xml_f:
                xml_str = xml_f.read()
                root = objectify.fromstring(xml_str)                
                meme_path = str(root['filename']).replace('\t','').replace('\n','')
                meme_path = self.image_dir + meme_path
                #display(Image(PATH, width=300, height=300))
                with open(meme_path, 'rb') as image_file:
                    # Encode image as base64 and str.
                    data = base64.b64encode(image_file.read())
                    data = str(data)

                text = str(root['object']['name']).replace('\t','').replace('\n','')
                text = re.search(r'\s{0,}(.*)', text).group(1)
                
                epis = str(root['folder']).replace('\t','').replace('\n','')
                epis = re.search(r'\s{0,}(.*)', epis).group(1)

            return text, epis, data

        def image_result_json(self, query, max_image_num, min_similarity):
            # Filling Json with multiple images.
            # meme_dict{{ text : img_bytes }, { text2 : img_bytes2 } ... }
            meme_dict = OrderedDict() 
            epi_dict = OrderedDict()            
            text_dict = OrderedDict()            
            sim_dict = OrderedDict()
            find_success = False

            query_vector = self.model.embed_sentence(query)
            
            if(np.any(query_vector)):
                find_success = True
                query_vector = np.array(query_vector[0], dtype=np.float32)
                most_sim_vectors = self.vector.similar_by_vector(query_vector)
                
                for img_num, xmlname_similarity in enumerate(most_sim_vectors):

                    if img_num >= max_image_num:
                        break
                    if xmlname_similarity[1] < min_similarity:
                        break

                    text, epis, data = self.get_text_and_bytes(xmlname_similarity[0])

                    meme_dict[xmlname_similarity[0]] = data
                    epi_dict[xmlname_similarity[0]] = epis
                    text_dict[xmlname_similarity[0]] = text
                    sim_dict[xmlname_similarity[0]] = xmlname_similarity[1] # vector similarity

            return self.rep_json(query, find_success, meme_dict, epi_dict, text_dict, sim_dict)
            
        def dank_dealer(self, request):
            send_back_results = []
            for query in request['queries']:
                # json_dump = json.dumps(self.image_result_json(req))
                res = self.image_result_json(query, request['max_image_num'], request['min_similarity'])
                send_back_results.append(res)

            return json.dumps(send_back_results)
        
        def random_dealer(self, request):
            meme_dict = {}
            epi_dict = {}
            text_dict = {}
            send_back_results = []
            ridx = randint(0, len(self.meme_list)-1)

            text, epis, data = self.get_text_and_bytes(self.meme_list[ridx])
            meme_dict[self.meme_list[ridx]] = data
            epi_dict[self.meme_list[ridx]] = epis
            text_dict[self.meme_list[ridx]] = text
            x = self.rep_json(None, True, meme_dict, epi_dict, text_dict, None)
            send_back_results.append(x)
            
            return json.dumps(send_back_results)
            
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
                
                self.logger.info('request\treq worker id %d: %s' % (int(self.worker_id), str(request['req_name'])))
                resp_json = ''
                
                if request['req_name'] == 'dank':
                    resp_json = self.dank_dealer(request)
                    
                elif request['req_name'] == 'random':
                    resp_json = self.random_dealer(request)
                
                # response.
                self.socket.send_string(resp_json)
                #time.sleep(1)
        
        def close(self):
            self.logger.info('shutting %d worker down...' %(self.worker_id))
            self.terminate()
            self.join()
            self.logger.info('%d worker terminated!' %(self.worker_id))
