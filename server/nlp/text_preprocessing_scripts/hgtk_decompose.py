from multiprocessing import Pool
import hgtk
from tqdm import tqdm

hf=open('hgtked_namu_extracted_deleted_127.txt', 'w')

total_text = None

def work(ttext):
  return hgtk.text.decompose(ttext)

print('reading text ...')
with open('namu_extracted_deleted_127.txt') as f:
  total_text = f.readlines()

print('processing ...')
with Pool() as pool:
  dcps = pool.map(work, total_text)
  for decomposed in tqdm(dcps):
    hf.write(decomposed)

hf.close()
