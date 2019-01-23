<h3> Clinet & Server :</h3>
*** 
<br>
<b>Client Usage :</b> <br>
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
https://github.com/sngjuk/meme-glossary/blob/master/example/client_example.png
<br>

<b>Server Usage :</b><br>
<sup>../scripts/</sup>
```
app.py --model_path=./model.bin --meme_dir=./3_manual_filtered_meme/ --xml_dir=./4_label_xml/ --vec_path=./5_meme_voca.vec
```

<h3>Prepare Memes from Comics :</h3>
---<br>
<b>1. </b> Crawl comics from web. Set episode_url in wt_crawler manually. <br>
<sup>../scripts/prepare_memes/</sup><br>
```
comics_crawler.py
```

result : 1_original_comics/ <br>
<br>
<b>2. </b> Cut comics into scenes. <br>
<sup>../scripts/prepare_memes/</sup>
```
cutter.py --kumiko=../scripts/prepare_memes/kumiko/ --meme_dir=./1_original_comics/ --out_dir=./2_kumiko_cut_meme/
```

result : 2_kumiko_cut/<br>
<br>
<b>3. </b> Filter error scenes manually. (GUI environment with sftp recommended) <br>
result : 3_manual_filtered_meme/<br>
<br>
<b>4-1. </b> Label with Google vision cloud API. Please check --lang_hint and pricing policy. <br>
<sup>export GOOGLE_APPLICATION_CREDENTIALS=/scripts/prepare_memes/google_vision_test/cred.json</sup> <br>
<sup>../scripts/prepare_memes/</sup>
```
auto_labeler.py --meme_dir=./3_manual_filtered_meme/ --output_dir=./4_label_xml/ --lang_hint=ko
```

<b>4-2. </b> or Label Manually. <br>
<sup>../scripts/prepare_memes/</sup>

```
manual_labeler.py --meme_dir=./3_manual_filtered_meme/ --output_dir=./4_label_xml/
```

<b>4-3. </b> or Label with Rect Label. (all xml format is standardized by Rect Label).<br>
https://rectlabel.com/ <br>
result : 4_label_xml/ <br>
<br>
<b>5. </b> Generate .vec file. {episode/filename : vectors} <br>
<sup>../scripts/prepare_memes/</sup>
```
xml2vec.py --model_path=./model.bin --meme_dir=./3_manual_filtered_meme --xml_dir=./4_label_xml/ --vec_path=./5_meme_voca.vec
```

result : 5_meme_voca.vec
<br>

<h3>Prepare Sentence Embedding Model :</h3>
---<br>
.bin file link will be added.
