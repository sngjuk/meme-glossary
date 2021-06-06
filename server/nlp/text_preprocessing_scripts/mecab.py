import sys
import codecs
import re
from sys import stdin
from konlpy.tag import Mecab
from konlpy.tag import Kkma

# MeCab installation needed
mecab = Mecab()

UTF8Reader = codecs.getreader('utf8')
sys.stdin = UTF8Reader(sys.stdin)

jpatt = re.compile('J.*')
spatt = re.compile('XSN')
fpatt = re.compile('SF')
upatt = re.compile('UNKNOWN')

vpatt = re.compile('V.*')
xpatt = re.compile('XSV')
npatt = re.compile('N.*')
x2patt = re.compile('XSA')

ms_reg = r'\/{1,}'
ms_reg2 = r'\s{2,}'

log_epch = 10000
f_size = 448453

dbg_line=None
testmod=None
#for test
if len(sys.argv) >2:
	testmod=sys.argv[1]
	dbg_line=int(sys.argv[2])

# this script basically no space for words,
# if word has meaningful pos, than separate,
# mwe is meant to be sticked together ( N.*, N.* -> N.*N.*)

f2 = open('namu_extracted_deleted_20_mecab.txt', 'w')
with open('namu_extracted_deleted_20.txt', 'r') as f:
	for ep, line in enumerate(f):
		line = line.replace(' ', '/')
		ps = mecab.pos(line)
		ps_helper = line.split('/')
		ms = mecab.morphs(line)

		#for tag debugging.
		if ep==dbg_line and testmod:
			print()
			print('ori : ', line)
			print()
			print('ps : ',ps)
			print()
			print('ps_hel : ', ps_helper)
			print()
			print('ms : ', ms)
			print()
	
		wt=''
		prev_tag='none'	
		# word in a line
		for i, p  in enumerate(ps):
			# this tags are deleted as /.
			if jpatt.match(p[1]) or spatt.match(p[1]) or fpatt.match(p[1]) or upatt.match(p[1]) :
				ms[i] ='/'
			# handling mwe
			elif npatt.match(p[1]) and npatt.match(prev_tag):
				pass
			# else meaningful tags have new space.
			elif vpatt.match(p[1]) or xpatt.match(p[1]) or x2patt.match(p[1]) or npatt.match(p[1]):
				#print('added!')
				#print('ori ms[i] ', ms[i])
				ms[i] = ' ' + ms[i]
				#print('ori ms[i] ', ms[i])

			# for mwe, if prev tag is N.* -> no space.
			prev_tag=p[1]


		if ep==dbg_line and testmod:
			print('ms mid : ', ms)

		# final result wt.
		for m in ms:
			wt+=m

		wt = wt.replace('.','')
		wt = re.sub(ms_reg,' ', wt)
		wt = re.sub(ms_reg2, ' ', wt)

		if wt[0] == ' ':
			wt = wt[1:]

		if ep%log_epch==0:
			print('epoch : ' +str(ep)+'/'+str(f_size)+'\n'+wt, end='')
			print('<EOL>')
			
		f2.write(wt + '\n')
		
		if ep==dbg_line and testmod:
			print(wt)
			break

f2.close()
