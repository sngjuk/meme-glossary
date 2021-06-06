<h3>- Prepare Memes from comic book. </h3>

Scripts are under ```prepare_memes``` folder.<br><br>
<b>1. </b> Crawl comics from web. <br>
<sup><i><b>Output :</b> Comic book image files. (original_comics) </i></sup>
```
prepare_memes/0-1_comics_crawler.py
```

<b>2. </b> Cut comics into scenes (memes). <br>
<sup><i><b>Input :</b> Comic book image files. (original_comics) [folder of folders of images] <br></i></sup> 
<sup><i><b>Output :</b> Cut scenes. (kumiko_cut_scenes) [folder of folders of images] </i> </sup>
```
prepare_memes/0-2_cut_comics_into_memes.py --kumiko= /prepare_memes/kumiko --meme_dir= original_comics --out_dir= kumiko_cut_scenes
```

<b>3. </b> Label with Google vision cloud API. <br>(Please check --lang_hint and pricing policy in this repo's <a href="https://github.com/sngjuk/meme-glossary/wiki/Google-vision-API-help-links">wiki page </a>.) <br>
<sup><i><b>Input :</b> Cut scenes. (kumiko_cut_scenes) <br></i></sup> 
<sup><i><b>Output :</b> Labeled xml. (labeled_xml) [folder of folders of xmls] <br></i> </sup>

```
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)"/google_vision_test/cred.json"
prepare_memes/1_label_memes_auto.py --meme_dir= kumiko_cut_scenes --output_dir= labeled_xml --lang_hint= '**'
```

<b>(Optional) </b> or Label with Rect Label using "name" tag. xml format is compatible with "RectLabel". 
https://rectlabel.com/ <br><br>


<b>4. </b> Embedding texts and save to pickle. <br>
<sup><i><b>Input :</b> Sentence embedding model, Labeled xml. (labeled_xml)<br></i></sup> 
<sup><i><b>Output :</b> saved_embedding.pickle. (saved_embedding.pickle) </i> </sup><br>

```
prepare_memes/2_embed_labels.py --model_path= model.bin --xml_dir= labeled_xml --saved_embedding= saved_embedding.pickle
```

Then the data is prepared.
<br><br>


<h3>- Prepare Sentence Embedding Model.</h3>

Pretrained models : <a href="https://github.com/sngjuk/sent2vec/tree/392428b294a6da9c91b6e705c14b8e2e408e34a7#downloading-pre-trained-models"> Pretrained Eng model </a> <br>
<b>Note :</b> To train a new sent2vec model, you first need some large training text file. This file should contain one sentence per line. The provided code does not perform tokenization and lowercasing, you have to preprocess your input data yourself.<br>


<h4>(Optional) 한국어 모델 - Korean model</h4>

1. <a href="https://drive.google.com/file/d/1--yfaeNHd_xpoJQxdNmTl16_QnhEm1Ma/view?usp=sharing">Pretrained KR model</a>(전처리한 나무위키 텍스트 220mb (부족한 데이터양으로 학습 후 모르는 단어가 꽤나 많습니다) <br>

2. <a href="https://drive.google.com/file/d/1LrrPlXH28mjqdimSEm3_07vFLptuM4LH/view?usp=sharing">Pretrained decomposed KR model</a> (자소분해 후 학습된 모델, 위 모델보다 나은 성능이지만 OOV 문제는 같습니다) <br>
<b><i>*자소 분해된 쿼리를 사용하기위해 2_embed_labels.py 와 app.py(server) 에 --lang=ko 옵션을 줍니다. </i> </b>
*hgtk 모듈 사용


<h3>- Start Server</h3>

```
./app.py --model_path model.bin --meme_dir= kumiko_cut_scenes --saved_embedding= saved_embedding.pickle
```
*Note: After server starts, first few queries have delay in inference.

<h3>- Start Client :</h3>
You can test with <br>

```
client/client_example.ipynb
```

![example](https://github.com/sngjuk/meme-glossary/blob/master/tutorial/client_example.png)