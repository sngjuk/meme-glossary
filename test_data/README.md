<b>Server Usage :</b><br>
```../scripts/app.py --model_path=./model.bin --vec_path=./5_test_meme_voca.vec```

<b>Client Usage :</b> <br>
```python
import client
mc = client.MgClient()

query = '잠'
mc.dank([query], max_img=3, min_sim=0.15) # Query with sentence.
mc.random() # Random meme
```

<b>Prepare Memes from Comics :</b><br>
1_ Crawl comics from web. Set episode_url in wt_crawler manually.</br>
```../scripts/comics_cutting/wt_crawler.py```
<br>
result : 1_original_comics/ <br>
<br>
2_ Cut comics into scenes.<br>
```../scripts/comics_cutting/cutter.py --kumiko=../scripts/comics_cutting/kumiko/ --image_dir=./1_original_comics/ --out_dir=./2_kumiko_cut/```
<br>
result : 2_kumiko_cut/<br>
<br>
3_ Filter error scenes manually. (GUI environment with sftp recommended) <br>
result : 3_manual_filtered_cut/<br>
<br>
4-1_ Label with Google vision cloud API. {free : 0-1K/month}, {$1.5 : 1K-5M/month}, {$0.6 : 5M+/month} {price/1K : count/month} <br>
```export GOOGLE_APPLICATION_CREDENTIALS=/path_to_credential/cred.json```
<br>
```../scripts/comics_cutting/auto_labeler.py --input_dir=./3_manual_filtered_cut/ --output_dir=./4_label_xml/```
<br><br>
4-2_ or Label Manually. <br>
```../scripts/comics_cutting/manual_labeler.py --input_dir=./3_manual_filtered_cut/ --output_dir=./4_label_xml/```
<br><br>
4-3_ or Label with Rect Label. (all xml format is standardized by Rect Label).<br>
https://rectlabel.com/ <br>
result : 4_label_xml/ <br>
<br>
5_ (Optional) Train own model and overwrite /meme-glossary/scripts/server/model.py <br>
result : Sentence_embed_model.bin <br>
<br>
6_ Generate .vec file. { xml_file_name : vectors } <br>
```../scripts/server/xml2vec.py --model_path=./model.bin --xml_dir=./4_label_xml/ --vec_path=./5_test_meme_voca.vec```
<br>
result : 5_test_meme_voca.vec
