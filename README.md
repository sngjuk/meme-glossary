# meme-glossary
* Retrieve meme-image with query sentence embedding over zmq.<br>
* Generate memes from comics.
<h2> Install </h2> python3 is required.

<h4>Client only usage : </h4>

```
git clone https://github.com/sngjuk/meme-glossary.git
./install.sh client
```

<h4>Full usage : </h4>

```
git clone --recurse-submodules https://github.com/sngjuk/meme-glossary.git
./install.sh all
``` 
<h2> Usage : </h2>

Please check ./example folder.
<br>

<b>Client :</b> <br>
```python
import client
mc = client.MgClient(ip='localhost', port=5555)

# Query with sentence.
mc.dank(['Nice to meet you'], max_img=3, min_sim=0.15)

# Random meme
mc.random()

# Save as a file.
mc.save_meme(img_data, 'image.jpg')
```

<b>Server :</b><br>
```
./app.py --model_path= model.bin --meme_dir= meme_dir --xml_dir= xml_dir --vec_path= meme_voca.vec
```

<h2> Example : <b>(check in <a href=https://github.com/sngjuk/meme-glossary/tree/master/example> example </a> folder)</b></h2>

<h3>Prepare Memes from comic book. </h3>

<b>1. </b> Crawl comics from web. (Please find the source for memes.. this script crawls Korean comics) <br>
<sup><i><b>Output :</b> Comic book image files. (1_original_comics) </i></sup>
```
prepare_memes/comics_crawler.py
```

<b>2. </b> Cut comic book into scenes. <br>
<sup><i><b>Input :</b> Comic book image files. (1_original_comics) <br></i></sup> 
<sup><i><b>Output :</b> Cut Scenes. (2_kumiko_cut_meme) </i> </sup>
```
prepare_memes/cutter.py --kumiko= /prepare_memes/kumiko --meme_dir= 1_original_comics --out_dir= 2_kumiko_cut_meme
```


<b>3. </b> Filter error cuts manually. (GUI environment is recommended.) <br>
<sup>
<i><b>Input :</b> Cut Scenes. (2_kumiko_cut_meme)<br> </i> </sup> 
<sup><i><b>Output :</b> Manually filtered memes. (3_manual_filtered_meme) </i></sup><br>


<b>4-1. </b> Label with Google vision cloud API. (Please check --lang_hint and pricing policy in this repo's <a href="https://github.com/sngjuk/meme-glossary/wiki/Google-vision-API-help-links">wiki page </a>.) <br>
<sup><i><b>Input :</b> Manually filtered memes. (3_manual_filtered_meme) <br></i></sup> 
<sup><i><b>Output :</b> Meme label xml. (4_label_xml) <br></i> </sup>

```
prepare_memes/auto_labeler.py --meme_dir= 3_manual_filtered_meme --output_dir= 4_label_xml --lang_hint= ' '
```

<b>4-2. </b> or Label Manually. <br>

```
prepare_memes/manual_labeler.py --meme_dir= 3_manual_filtered_meme --output_dir= 4_label_xml
```

<b>4-3. </b> or Label with Rect Label. (xml format is sharable with Rect Label). <br>
https://rectlabel.com/ <br><br>


<b>5. </b> Generate .vec for similiarity search. {episode/filename : vector} <br>
<sup><i><b>Input :</b> Meme label xml. (4_label_xml), Sentence embedding model. (model.bin) -please check below.  <br></i></sup> 
<sup><i><b>Output :</b> .vec file for similiarity search. (5_meme_voca.vec) </i> </sup><br>

```
prepare_memes/xml2vec.py --model_path= model.bin --xml_dir= 4_label_xml --vec_path= 5_meme_voca.vec
```

<h3>Prepare Sentence Embedding Model.</h3>

Pretrained models : <a href="https://github.com/sngjuk/sent2vec/tree/392428b294a6da9c91b6e705c14b8e2e408e34a7#downloading-pre-trained-models"> Pretrained Eng model </a> <br>
<b>Note :</b> To train a new sent2vec model, you first need some large training text file. This file should contain one sentence per line. The provided code does not perform tokenization and lowercasing, you have to preprocess your input data yourself.<br>
*You can replace nlp model(not sent2vec) by simply chainging /server/nlp/model.py <br><br>
<h4> 한국어 모델 </h4>

1. <a href="https://drive.google.com/file/d/1--yfaeNHd_xpoJQxdNmTl16_QnhEm1Ma/view?usp=sharing">Pretrained KR model</a>(전처리한 나무위키 텍스트 220mb (부족한 데이터양으로 학습 후 모르는 단어가 꽤나 많습니다) <br>

2. <a href="https://drive.google.com/file/d/1LrrPlXH28mjqdimSEm3_07vFLptuM4LH/view?usp=sharing">Pretrained decomposed KR model</a> (자소분해 후 학습된 모델, 위 모델보다 나은 성능이지만 OOV 문제는 같습니다) <br>
<b><i>*자소 분해된 쿼리를 사용하기위해 xml2vec.py, app.py에 --lang=ko 옵션을 줍니다. </i> </b>

<h3>Done! execute server :</h3>

```
./app.py --model_path model.bin --meme_dir= 3_manual_filtered_meme --xml_dir= 4_label_xml --vec_path= 5_meme_voca.vec (--lang=ko <- 자소분해모델 사용시 추가)
```

<h3>Test with Client :</h3>

![example](https://github.com/sngjuk/meme-glossary/blob/master/example/client_example.png)
