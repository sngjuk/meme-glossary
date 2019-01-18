Server Usage : <br><br>

1. Crawl comics from web. Set episode_url in wt_crawler manually.<br>
./scripts/comics_cutting/wt_crawler.py
result : 1_original_comics/ <br>
<br>
2. Cut comics into scenes.<br>
./cutter.py --kumiko=/kumiko/ -i=/1_original_comics/ -o=/2_kumiko_cut/<br>
result : 2_kumiko_cut/<br>
<br>
3. Filter error scenes manually. (GUI environment with sftp recommended) <br>
result : 3_manual_filtered_cut/<br>
<br>
4-1. Label with Google vision cloud API. {free : 0-1K/month}, {$1.5 : 1K-5M/month}, {$0.6 : 5M+/month} {price/1K : count/month}<br>
./auto_labeler.py -i=/3_manual_filtered_cut/ -o=/test_data/4_label_xml/ <br>
<br>
4-2. or Label with Rect Label program. (all xml format is standardized with Rect Label).
https://github.com/ryouchinsa/Rectlabel-support <br>
<br>
5. (Optional) Train own model and overwrite /meme-glossary/scripts/server/model.py <br>
<br>
6. Generate .vec file. { xml_file_name : vectors } <br>
./xml2vec.py --model=/model.bin --xml_path=/4_label_xml/ -vec_file_name=/5_test_meme_voca.vec <br>
result : 5_test_meme_voca.vec <br>
<br>
7. Start server. <br>
./app.py --model=/model.bin --voca=/5_test_meme_voca.vec <br>
<br>
<br>
Client Usage : <br><br>

import client <br>
mc = client.MgClient()<br>
query = '고양이'<br>
mc.dank([query], max_img=3, min_sim=0.15)<br>
mc.random() # Random meme<br>
<br>