import sent2vec
# hgtk is only for KR preprocessing. 
import hgtk

class EmbedModel:
    def __init__(self, lang=None):
        self.lang = lang

    def load_model(self, model_path):
        # Load model.
        self.model = sent2vec.Sent2vecModel()
        self.model_path = model_path
        self.model.load_model(model_path)
    
    def embed_sentence(self, query_string):
        # Embedding is list of list e.g. [[0.5513, 0.1205, ...]]
        # Vector length will be detected by xml2vec.py automatically, So any 1-dim vector is compatible.
        # 'self.lang' is only for Korean sentence preprocessing.
        
        if self.lang=='ko':
            return self.model.embed_sentence(hgtk.text.decompose(query_string))
        else :
            return self.model.embed_sentence(query_string)
    
    def __del__(self):
        pass

    def __exit__(self):
        pass
