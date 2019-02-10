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
mc = client.MgClient()

# Query with sentence.
mc.dank(['Nice to meet you'], max_img=3, min_sim=0.15)

# Random meme
mc.random()

# Save as a file.
mc.save_meme(img_data, 'image.jpg')
```

<b>Server :</b><br>
```
./app.py --model_path=model.bin --meme_dir=meme_dir/ --xml_dir=xml_dir/ --vec_path=meme_voca.vec
```
<br>
