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
