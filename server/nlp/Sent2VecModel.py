import sent2vec
import faiss
import hgtk

class Sent2VecModel():
    def __init__(self, lang=None):
        self.model = None
        self.model_path = None
        self.lang = lang

    def load_model(self, model_path):
        # Load model.
        self.model = sent2vec.Sent2vecModel()
        self.model_path = model_path
        self.model.load_model(model_path)

    def embed_sentence(self, query_string):
        # 'self.lang' is for additional tokenizing only for korean, for better performance
        embedding = None
        if self.lang == 'ko':
            embedding = self.model.embed_sentence(hgtk.text.decompose(query_string))
        else:
            embedding = self.model.embed_sentence(query_string)
        
        faiss.normalize_L2(embedding)
        return embedding

    def __del__(self):
        pass

    def __exit__(self):
        pass
