import sent2vec

class EmbedModel:
    def __init__(self):
        pass

    def load_model(self, model_path):
        self.model = sent2vec.Sent2vecModel()
        self.model_path = model_path
        self.model.load_model(model_path)
    
    def embed_sentence(self, query_string):
        # Embedding shape : [[0.55135, 0.1202502, -0.464142 ...]]
        return self.model.embed_sentence(query_string)
