# server client
# Infrence from user input and search for .vec file using Gensim.
import os
from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors
import numpy as np
from collections import OrderedDict
from numpy import dot
import re
from numpy.linalg import norm
from IPython.display import Image
from IPython.core.display import Image, display

from lxml import objectify
import array
import sent2vec
from gensim.models import FastText
import base64
import json

import time
import threading
import zmq
from server.helper import set_logger

class MgServer(threading.Thread):
    def __init__(self, args):
        super().__init__()
        """Server routine"""
        self.logger = set_logger('VENTILATOR')
        self.model_path = args.model_path
        self.vec_path = args.vec_path
        self.meme_xml_path = args.meme_xml_path
        self.port = args.port
        
        self.url_worker = "inproc://workers"
        self.url_client = "tcp://*:" + self.port
        self.logger.info('opend server : %s' %(self.url_client))
        
        # Load model
        self.logger.info('loading model...')
        self.model = sent2vec.Sent2vecModel()
        self.model.load_model(self.model_path)
        self.word_vector = KeyedVectors.load_word2vec_format(self.vec_path)
        self.logger.info('loading model done')

        # Prepare our context and sockets
        self.context = zmq.Context.instance()

        # Socket to talk to clients
        self.clients = self.context.socket(zmq.ROUTER)
        self.clients.bind(self.url_client)

        # Socket to talk to workers
        self.workers = self.context.socket(zmq.DEALER)
        self.workers.bind(self.url_worker)
        print('after proxy')
        
    def run(self):
        # Launch pool of worker threads
        self.threads = []
        for i in range(5):
            #thread = threading.Thread(target=worker_routine, args=(url_worker,i,))
            thread = MgServer.MgWorker(worker_url=self.url_worker, worker_id=i, 
                                       model=self.model, vector=self.word_vector, 
                                       meme_xml_path=self.meme_xml_path)
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
        def __init__(self, worker_url, worker_id, model, vector, meme_xml_path, context=None):
            super().__init__()
            self.logger = set_logger('WORKER-%d' % worker_id)
            self.worker_url = worker_url
            self.worker_id = worker_id
            self.model = model
            self.vector = vector
            self.meme_xml_path = meme_xml_path
            self.context = context

        def get_text_and_bytes(self, xml_file_name):
            #meme_path = self.meme_path+ xml_file_name.rsplit('-', 1)[0] +'/' + xml_file_name.split('.')[0] + '.jpg'
            text = None
            epis = None
            data = None
            with open(xml_file_name) as xml_f:
                xml_str = xml_f.read()
                root = objectify.fromstring(xml_str)                
                meme_path = str(root['filename']).replace('\t','').replace('\n','')
                #display(Image(PATH, width=300, height=300))
                with open(meme_path, 'rb') as image_file:
                    # Encode image as base64 and str.
                    data = base64.b64encode(image_file.read())
                    data = str(data)

                #with open(self.meme_xml_path+xml_file_name.rsplit('-', 1)[0].replace('-','_')+'/'+xml_file_name) as xml_file:
                text = str(root['object']['name']).replace('\t','').replace('\n','')
                text = re.search(r'\s{0,}(.*)', text).group(1)
                
                epis = str(root['folder']).replace('\t','').replace('\n','')
                epis = re.search(r'\s{0,}(.*)', epis).group(1)

            return text, epis, data

        def image_result_json(self, query, max_image_num, min_similarity):
            # Filling Json with multiple images.
            # script, image and episode.
            find_success = False
            # meme_dict{{ text : img_bytes }, { text2 : img_bytes2 } ... }
            meme_dict = OrderedDict() 
            epi_dict = OrderedDict()            
            text_dict = OrderedDict()            
            sim_dict = OrderedDict()

            query_vector = self.model.embed_sentence(query)
            
            if(np.any(query_vector)):
                find_success = True
                query_vector = np.array(query_vector[0], dtype=np.float32)
                most_sim_vectors = self.vector.similar_by_vector(query_vector)
                print(most_sim_vectors)
                
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
                    
            x = {
              "query": query,
              "find_success": find_success,
              "memes": meme_dict,
              "episodes": epi_dict,
              "texts" : text_dict,
              "sims" : sim_dict
            }
            return x
            
        def run(self):
            """Worker routine"""
            self.context = self.context or zmq.Context.instance()
            # Socket to talk to dispatcher
            self.socket = self.context.socket(zmq.REP)
            self.socket.connect(self.worker_url)

            while True:
                self.logger.info('request\treq worker id %d: ' % (int(self.worker_id)))
                # Need to modification with json.
                print('wating for query')
#               query  = self.socket.recv().decode("utf-8")
                request = self.socket.recv_string()
                requests = json.loads(request)
                
                print('type of  requests["queris"] :', type(requests['queries']))
                send_back_results = []
                for query in requests['queries']:
                    #json_dump = json.dumps(self.image_result_json(req))
                    res = self.image_result_json(query, requests['max_image_num'], requests['min_similarity'])
                    send_back_results.append(res)                    
                
                result_json = json.dumps(send_back_results)
                self.socket.send_string(result_json)
                '''
                for i in most_sim_vectors:
                    self.print_pic_sent(self.meme_path, self.meme_xml_path, i[0])
                    break
                '''
                # do some 'work'
                '''
                with open("/root/Meme-Glossary/scripts/service/test_image.jpg", "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read())
                    socket.send(encoded_string)
                '''
                time.sleep(1)
        
        def close(self):
            self.logger.info('shutting %d worker down...' %(self.worker_id))
            self.terminate()
            self.join()
            self.logger.info('terminated!')
