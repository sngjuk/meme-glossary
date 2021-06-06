import tensorflow_hub as hub
import numpy as np
import tensorflow_text
import faiss
import hgtk


class TensorflowModel():
    def __init__(self, lang=None):
        self.model = None
        self.model_path = None
        self.lang = lang

    def load_model(self, model_path):
        # Load model.
        self.model = hub.load(model_path)

    def embed_sentence(self, query_string):
        # 'self.lang' is for additional tokenizing only for korean, for better performance
        embedding = None
        if self.lang == 'ko':
            embedding = self.model(hgtk.text.decompose(query_string)).numpy()
        else:
            embedding = self.model(query_string).numpy()
        
        faiss.normalize_L2(embedding)
        return embedding

    def __del__(self):
        pass

    def __exit__(self):
        pass
