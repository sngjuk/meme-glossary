#!/usr/bin/env python3

import os
import re
import sys

print('please set min_sentence_len: ')
min_sentence_len = int(input())
outfile='namu_extracted_deleted.txt'
max_sentence_len = 9999

if len(sys.argv) >1:
    max_sentence_len=int(sys.argv[2])

outfile = outfile.rsplit('.')[0] + '_'  + str(min_sentence_len) + '.txt'

#not korean.
regex0 = r'[^가-힣\s\.]'
#word with decimals.
regex1 = r'\w*\d\w*'
#word with english.
regex2 = r'\w*[A-Za-z]\w*'

reg2 = r'\.+'
reg_mw = r'\s+'
reg_mn = r'\n+'
epch=100000
total_length=45038943

DMODE = False
line_cnt = 0

print('output file: %s' % outfile)

if os.path.isfile(outfile):
    print('output file exists')
    sys.exit()

f2= open(outfile, 'w')
with open('namu_extracted.json', 'r') as f:
    for i, line in enumerate(f):
        
        if DMODE:
            print('=======================')
            print('original: ' + line)		
        r1 = re.sub(regex1, '', line)
        if DMODE:
            print('r1: ' + r1)
        r2 = re.sub(regex2, '', r1)
        if DMODE:
            print('r2: ' + r2)
        r3 = re.sub(regex0, '', r2)
        if DMODE:
            print('r3: ' + r3)

        t= re.sub(r'\n', '', r3)
        if DMODE:
            print('remove newline: ' + t)
        t= re.sub(r'\.+', '\n', r3)
        if DMODE:
            print('remove multiple dots to new line: ' + t)
        #t= t.replace('.','\n')
        t= re.sub(r'\ +', ' ', t)
        if DMODE:
            print('remove multiple withe: ' + t)
        #t= re.sub(reg_mn, '', t)
        t= re.sub(r'\ *\n+\ *', '\n', t)
        if DMODE:
            print('remove starting space: ' + t)
        
        #t= re.search(r'\n*(.*)\n*', t).group(1)
        t= re.search(r'\s*(.*)\s*', t).group(1)

        if len(t) >= min_sentence_len and len(t) < max_sentence_len:
            f2.write(t + '\n')
            line_cnt += 1
            #print(str(len(x)),x+'\n', end='')
            
            if DMODE:
                print('\nfilnal: ' + t)
                break

        if i%epch==0:
            print('epch '+str(i) + '/' + str(total_length) + ':' + t + ' - ' + str(len(t)))
            print('line count: %d' % line_cnt)

f2.close()
print('done: sentence count: ' + str(line_cnt))

