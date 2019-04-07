#!/bin/sh

if [ "$#" -ne 1 ]; then
    echo "Argument required : 'client' or 'full'"
    exit 1
fi;

if [ "$1" = "client" ]
then 
    pip3 install -r client_pip_list.txt
elif [ "$1"  = "all" ]
then
    sudo apt-get install imagemagick
    pip3 install -r requirements.txt
    cd server/nlp/sent2vec/
    make
    pip3 install .
fi;
