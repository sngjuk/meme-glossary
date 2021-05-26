import tensorflow_hub as hub
import numpy as np
import tensorflow_text
import hgtk
from server.nlp.model import IEmbedModel


class TensorflowModel(IEmbedModel):
    def __init__(self, lang=None):
        self.lang = lang
        self.model = None
        self.model_path = None

    def load_model(self, model_path):
        # Load model.
        self.model = hub.load(model_path)

    def embed_sentence(self, query_string):
        # Embedding is list of list e.g. [[0.5513, 0.1205, ...]]
        # Vector length will be detected by label_embedder.py automatically, So any 1-dim vector is compatible.
        # 'self.lang' is only for Korean sentence preprocessing.

        return self.model(query_string)

    def __del__(self):
        pass

    def __exit__(self):
        pass
