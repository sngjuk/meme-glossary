import sent2vec

class EmbedModel:
    def __init__(self):
        pass

    def load_model(self, model_path):
        self.model = sent2vec.Sent2vecModel()
        self.model_path = model_path
        self.model.load_model(model_path)
    
    def embed_sentence(self, query_string):
        # Return Embedding structure is list of list : [[0.5513, 0.1205, ...]]
        # Detect vector length in xml2vec.py, So any 1-dim vector is possible.
        res = self.model.embed_sentence(query_string)
        return res
    
    def __del__(self):
        # https://github.com/epfml/sent2vec/commit/5cdffc5551c7b1ea54b11785d4037b946367ca96
        self.model.release_shared_mem(self.model_path)
        
    def __exit__(self):
        self.model.release_shared_mem(self.model_path)
