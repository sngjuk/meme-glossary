#!/usr/bin/env python3

from service.server import ServerTask

def main():
    #main function
    server = ServerTask()
    server.start()
#    for i in range(3):
#        client = ClientTask(i)
#        client.start()

    server.join()

if __name__ == "__main__":
    main()
