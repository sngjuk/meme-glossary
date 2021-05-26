#!/bin/bash
#path to authentication .json file.
#To use tagger.py, export GOOGLE_APPLICATION_CREDENTIALS with path of credential json file explicitly. 

DIR=$(pwd)
export GOOGLE_APPLICATION_CREDENTIALS=$DIR"/cred.json"
echo $GOOGLE_APPLICATION_CREDENTIALS
python3 detect_text.py
