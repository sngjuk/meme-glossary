#!/usr/bin/env python3

import zmq
import sys
import threading
import time
from random import randint, random

__author__ = "Felipe Cruz <felipecruz@loogica.net>"
__license__ = "MIT/X11"

def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()
    

class ServerTask(threading.Thread):
    """ServerTask"""
    def __init__(self):
        threading.Thread.__init__ (self)

    def run(self):
        with zmq.Context() as context, context.socket(zmq.ROUTER) as frontend, context.socket(zmq.DEALER) as backend:
            frontend.bind('tcp://*:5571')
            backend.bind('inproc://backend')
            
            workers = []
            for i in range(5):
                worker = ServerWorker(context)
                worker.start()
                workers.append(worker)

            zmq.proxy(frontend, backend)

            #frontend.close()
            #backend.close()
            #context.term()

class ServerWorker(threading.Thread):
    """ServerWorker"""
    def __init__(self, context):
        threading.Thread.__init__ (self)
        self.context = context

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        tprint('Worker started')
        while True:
            ident, msg = worker.recv_multipart()
            tprint('Worker received %s from %s' % (msg, ident))
            replies = randint(0,4)
            for i in range(replies):
                time.sleep(1. / (randint(1,10)))
                worker.send_multipart([ident, msg])

        worker.close()

