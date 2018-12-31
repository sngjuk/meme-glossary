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

class MgClient:
    """MgClient"""
    def __init__(self, ip='localhost', port=5555, port_out=5556, output_fmt='ndarray', show_server_config=False, identity=None):
        self.context = zmq.Context()
        self.sender = self.context.socket(zmq.PUSH)
        self.identity = identity or str(uuid.uuid4()).encode('ascii')
        self.sender.connect('tcp://%s:%d' % (ip, port))
        
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.setsockopt(zmq.SUBSCRIBE, self.identity)
        self.receiver.connect('tcp://%s:%d' % (ip, port_out))
        
        self.request_id = 0
        self.pending_request = set()
        
        self.output_fmt = output_fmt
        self.port = port
        self.port_out = port_out
        self.ip = ip
        
        if show_server_config:
            self._print_dict(self.server_status, 'server config:')
            
    def _send(self, msg):
        self.sender.send_multipart([self.identity, msg, b'%d' % self.request_id])
        self.pending_request.add(self.request_id)
        self.request_id += 1

    def _recv(self):
        response = self.receiver.recv_multipart()
        request_id = int(response[-1])
        self.pending_request.remove(request_id)
        return Response(request_id, response)
    
    
    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        identity = u'worker-%d' % self.id
        socket.identity = identity.encode('ascii')
        socket.connect('tcp://localhost:5571')
        print('Client %s started' % (identity))
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)
        reqs = 0
        while True:
            reqs = reqs + 1
            print('Req #%d sent..' % (reqs))
            socket.send_string(u'request #%d' % (reqs))
            for i in range(5):
                sockets = dict(poll.poll(1000))
                if socket in sockets:
                    msg = socket.recv()
                    tprint('Client %s received: %s' % (identity, msg))

        socket.close()
        context.term()