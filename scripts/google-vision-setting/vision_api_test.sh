#!/bin/bash
#path to authentication .json file.
#To use tagger.py, export GOOGLE_APPLICATION_CREDENTIALS with path of credential json file explicitly. 

export GOOGLE_APPLICATION_CREDENTIALS="/root/studio/scripts/google-vision-setting/cred.json"
python3 detect_text.py
