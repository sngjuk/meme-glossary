
<b>Client :</b> <br>
```python
import client
mc = client.MgClient()

# Query with sentence.
mc.dank(['잠', '안녕 반가워', ...], max_img=3, min_sim=0.15) 
# Random meme
mc.random()
# Save as a file.
mc.save_meme(img_data, 'image.jpg')
```

<b>Server :</b><br>
```
app.py --model_path model.bin --meme_dir 3_manual_filtered_meme --xml_dir 4_label_xml --vec_path 5_meme_voca.vec
```

<h3>Prepare Memes from Comics :</h3>

<b>1. </b> Crawl comics from web. (Please find the source for memes.. this script crawls Korean comics) <br>
<sup><i><b>Output :</b> Comic book image files. (1_original_comics/) </i></sup>
```
comics_crawler.py
```

<b>2. </b> Cut comics into scenes. <br>
<sup><i><b>Input :</b> Comic book images. (1_original_comics/) <br></i></sup> 
<sup><i><b>Output :</b> Cut Scenes. (2_kumiko_cut_meme/) </i> </sup>
```
cutter.py --kumiko /prepare_memes/kumiko/ --meme_dir 1_original_comics/ --out_dir 2_kumiko_cut_meme/
```

<br>
<b>3. </b> Filter error cut manually. (GUI environment is recommended.) <br>
<sup>
<i><b>Input :</b> Cut memes. (2_kumiko_cut_meme/)<br> </i> </sup> 
<sup><i><b>Output :</b> Manually filtered memes. (3_manual_filtered_meme/) </i></sup><br> <br>


<b>4-1. </b> Label with Google vision cloud API. Please check --lang_hint and pricing policy. <br>
<sup><i><b>Input :</b> Manually filtered memes. (3_manual_filtered_meme/) <br></i></sup> 
<sup><i><b>Output :</b> Meme label xml. (4_label_xml/) <br></i> </sup>

```
auto_labeler.py --meme_dir 3_manual_filtered_meme --output_dir 4_label_xml --lang_hint en or ko
```
<sup>export GOOGLE_APPLICATION_CREDENTIALS=cred.json</sup> 

<b>4-2. </b> or Label Manually. <br>

```
manual_labeler.py --meme_dir 3_manual_filtered_meme/ --output_dir 4_label_xml/
```

<b>4-3. </b> or Label with Rect Label. (all xml format is standardized by Rect Label). <br>
https://rectlabel.com/ <br> <br>


<b>5. </b> Generate .vec file. {episode/filename : vectors} <br>
<sup><i><b>Input :</b> Meme label xml. (4_label_xml/)  <br></i></sup> 
<sup><i><b>Output :</b> .vec file for similiarity search. (5_meme_voca.vec) </i> </sup><br>

```
xml2vec.py --model_path model.bin --xml_dir 4_label_xml/ --vec_path 5_meme_voca.vec
```
<br>

<h3>Prepare Sentence Embedding Model.bin :</h3>
* To train a new sent2vec model, you first need some large training text file. This file should contain one sentence per line. The provided code does not perform tokenization and lowercasing, you have to preprocess your input data yourself.<br>
Please check server/nlp/sent2vec/README.md <br><br>

KR : 전처리한 나무위키 텍스트 220mb (부족한 데이터양으로 학습 후 모르는 단어가 꽤나 많습니다.) <br>
https://drive.google.com/file/d/1--yfaeNHd_xpoJQxdNmTl16_QnhEm1Ma/view?usp=sharing <br>
```
./fasttext sent2vec -input lined_namu200mb.txt -output lr2_epch6_ng1_min8_model.bin -minCount 8 -dim 700 -epoch 6 -lr 0.2 -wordNgrams 1 -loss ns -neg 10 -thread 20 -t 0.000005 -dropoutK 4 -minCountLabel 20 -bucket 4000000
```
KR2 : hgtk 자소분해한 나무위키 텍스트 700mb. 더 나은 성능을 보이지만 위와 같은 문장들이기에 OOV는 여전합니다. <br>
<i>*hgtk로 분해된 쿼리를 사용하기위해 xml2vec.py, app.py에 --lang=ko 옵션을 추가로 줍니다. </i> <br>
https://drive.google.com/file/d/1LrrPlXH28mjqdimSEm3_07vFLptuM4LH/view?usp=sharing <br>
```
./fasttext sent2vec -input hgtked_lined_namu200mb.txt -output hg_ep11lr2wn2 -minCount 8 -dim 700 -epoch 11 -lr 0.2 -wordNgrams 2 -loss ns -neg 10 -thread 20 -t 0.000005 -dropoutK 4 -minCountLabel 20 -bucket 4000000
```

<h3>Example :</h3>

![example](https://github.com/sngjuk/meme-glossary/blob/master/example/client_example.png)
