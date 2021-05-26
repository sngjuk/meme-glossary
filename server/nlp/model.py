import sent2vec
import hgtk


class IEmbedModel:
    def __init__(self, lang=None):
        self.lang = lang

    def load_model(self, model_path: str):
        # Load model.
        pass

    def embed_sentence(self, query_string: str) -> list:
        # Embedding is list of list e.g. [[0.5513, 0.1205, ...]]
        # Vector length will be detected by label_embedderlabel_embedder.py automatically, So any 1-dim vector is compatible.
        # 'self.lang' is only for Korean sentence preprocessing.
        pass

    def __del__(self):
        pass

    def __exit__(self):
        pass
