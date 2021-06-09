"""
Serve 'dank', 'random' request from MgClient with ZMQ.
"""
import os
import faiss
import numpy as np
import random
import re
import base64
import json
import threading
import zmq
import pickle
from collections import OrderedDict
from lxml import objectify
from datetime import datetime
from .helper import set_logger

class MgServer(threading.Thread):
    def __init__(self, args):
        super().__init__()
        random.seed(datetime.now())
        
        """Server routine"""
        self.logger = set_logger('VENTILATOR')
        self.model_path = os.path.abspath(args.model_path)
        self.meme_dir = os.path.abspath(args.meme_dir)
        self.saved_embedding_path = os.path.abspath(args.saved_embedding)
        self.lang = args.lang
        self.port = args.port
        self.thread_num = args.thread_num
        
        self.url_worker = "inproc://workers"
        self.url_client = "tcp://*:" + self.port
        self.logger.info('opend server : %s' %(self.url_client))
        self.logger.info('num of threads : %s' %(self.thread_num))
        
        # Load model
        self.logger.info('loading model...')
        self.logger.info('model type: %s' % args.model_type)
        self.model = None
        if args.model_type == 'tf':
            from .nlp.TensorflowModel import TensorflowModel
            self.model = TensorflowModel(self.lang)
        elif args.model_type == 'sent2vec':
            from .nlp.Sent2VecModel import Sent2VecModel
            self.model = Sent2VecModel(self.lang)

        self.model.load_model(self.model_path)
        self.logger.info('model load done.')
        
        # Load saved embedding
        self.saved_embedding = pickle.load(open(self.saved_embedding_path, 'rb'))

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
                                       meme_dir=self.meme_dir, saved_embedding=self.saved_embedding)
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
        def __init__(self, worker_url, worker_id, model, meme_dir, saved_embedding, context=None):
            super().__init__()
            self.logger = set_logger('WORKER-%d ' % worker_id)
            self.worker_url = worker_url
            self.worker_id = worker_id
            self.model = model
            self.meme_dir = meme_dir
            self.saved_embedding = saved_embedding
            self.context = context

            # build index
            self.index = faiss.IndexFlatIP(self.saved_embedding['embedding_dimension'])
            self.index.add(self.saved_embedding['embedding'])
            self.logger.info('saved_embedding.pickle load done.')            
            
        def rep_json(self, rep_name, query, oov_flag, result_exist_flag, 
                     memefname_list, episode_list, text_list, imgdata_list, sim_list):

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
            value = re.search(r'\s*(.*)', value).group(1)
            return value
        
        def get_text_and_bytes(self, embedding_index):
            # xml_file_name : episode/some.xml

            meme_fname, episode = self.saved_embedding['file_path'][embedding_index].split('/')
            text = self.saved_embedding['text'][embedding_index]

            meme_path = os.path.join(self.meme_dir, 
                                     self.saved_embedding['file_path'][embedding_index])
            with open(meme_path, 'rb') as meme_file:
                # Encode image with base64 and str.
                data = base64.b64encode(meme_file.read())
                data = str(data)

            return meme_fname, episode, text, data

        def image_result_json(self, query, request):
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

            query_embedding = self.model.embed_sentence(query)

            if(np.any(query_embedding[0])):
                oov_flag = False

                D, I = self.index.search(x=query_embedding, k= request['max_result_num'])
                sim_list = [float(x) for x in D[0].tolist()]
                index_list = I[0]

                #query_vector = np.array(query_vector[0], dtype=np.float32)

                for similarity, embedding_index in zip(sim_list, index_list):
                    if similarity < request['min_similarity']:
                        break

                    meme_fname, episode, text, data = self.get_text_and_bytes(embedding_index)

                    memefname_list.append(meme_fname)
                    episode_list.append(episode)                    
                    text_list.append(text)
                    imgdata_list.append(data)
                    sim_list.append(similarity)

                if len(imgdata_list):
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
            ridx = random.randint(0, len(self.saved_embedding['text']) - 1)

            meme_fname, episode, text, data = self.get_text_and_bytes(ridx)
            memefname_list.append(meme_fname)
            episode_list.append(episode)
            text_list.append(text)
            imgdata_list.append(data)
            
            rep_json = self.rep_json(request['req'], query=None, oov_flag=False, 
                                     result_exist_flag=True, memefname_list=memefname_list,
                                     episode_list=episode_list, text_list=text_list, 
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
                
                self.logger.info('request\treq worker id %d: %s %s' % (int(self.worker_id),
                                                                       str(request['req']),
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
