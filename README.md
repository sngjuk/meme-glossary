# meme-glossary
* Retrieve meme-image with query sentence embedding over zmq.<br>
* Generate memes from comics.
<h2> Install </h2> 

<h4>Server(nlp) & Client </h4>

```
git clone --recurse-submodules https://github.com/sngjuk/meme-glossary.git
./install.sh all
``` 

<h4>Client only : </h4>

```
git clone https://github.com/sngjuk/meme-glossary.git
./install.sh client
```

<h2> Usage : </h2>

Please check <a href=https://github.com/sngjuk/meme-glossary/tree/master/tutorial>tutorial</a>
<br>

<b>Server :</b><br>
```
./app.py --model_path model.bin --meme_dir meme_dir --saved_embedding saved_embedding.pickle
```

<b>Client :</b> <br>
```python
import client
mg = client.MgClient(ip='localhost', port=5555)

# Query with sentence and get meme images.
mg.dank(['Nice to meet you'], max_img=3, min_sim=0.15)

# Random meme
mg.random()

# Save as a file.
mg.save_meme(img_data, 'image.jpg')
```
