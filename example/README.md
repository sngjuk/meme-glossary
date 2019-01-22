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
```../scripts/app.py --model_path=./model.bin --meme_dir=./3_manual_filtered_meme/ --xml_dir=./4_label_xml/ --vec_path=./5_meme_voca.vec```
<br><br>
<b>Prepare Memes from Comics :</b><br>
1_ Crawl comics from web. Set episode_url in wt_crawler manually.</br>
```../scripts/prepare_memes/comics_crawler.py```
<br>
result : 1_original_comics/ <br>
<br>
2_ Cut comics into scenes.<br>
```../scripts/prepare_memes/cutter.py --kumiko=../scripts/prepare_memes/kumiko/ --meme_dir=./1_original_comics/ --out_dir=./2_kumiko_cut_meme/```
<br>
result : 2_kumiko_cut/<br>
<br>
3_ Filter error scenes manually. (GUI environment with sftp recommended) <br>
result : 3_manual_filtered_meme/<br>
<br>
4-1_ Label with Google vision cloud API. Please check --lang_hint and pricing policy. <br>
```export GOOGLE_APPLICATION_CREDENTIALS=/root/meme-glossary/scripts/prepare_memes/google_vision_test/cred.json```
<br>
```../scripts/prepare_memes/auto_labeler.py --meme_dir=./3_manual_filtered_meme/ --output_dir=./4_label_xml/ --lang_hint=ko```
<br><br>
4-2_ or Label Manually. <br>
```../scripts/prepare_memes/manual_labeler.py --meme_dir=./3_manual_filtered_meme/ --output_dir=./4_label_xml/```
<br><br>
4-3_ or Label with Rect Label. (all xml format is standardized by Rect Label).<br>
https://rectlabel.com/ <br>
result : 4_label_xml/ <br>
<br>
5_ Generate .vec file. {episode/filename : vectors} <br>
```../scripts/prepare_memes/xml2vec.py --model_path=./model.bin --meme_dir=./3_manual_filtered_meme --xml_dir=./4_label_xml/ --vec_path=./5_meme_voca.vec```
<br>
result : 5_meme_voca.vec
<br><br>
<b>Prepare Sentence Embedding Model :</b><br>
.bin file link will be added.
