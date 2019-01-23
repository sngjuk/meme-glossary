#!/bin/sh

if [ "$#" -ne 1 ]; then
    echo "Argument required : 'client' or 'full'"
    exit 1
fi;

if [ "$1" = "client" ]
then 
    pip install -r client_pip_list.txt
elif [ "$1"  = "full" ]
then
    pip install -r requirements.txt
    cd ./scripts/server/nlp/sent2vec/
    make
    pip install .
fi;
