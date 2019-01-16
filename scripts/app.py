#!/usr/bin/env python3

from server.server import MgServer
from server.helper import get_args_parser

def main():
    #main function
    args = get_args_parser()
    server = MgServer(args)
    server.start()
    server.join()

if __name__ == "__main__":
    main()
