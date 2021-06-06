
class IEmbedModel:
    def __init__(self, lang=None):
        self.lang = lang

    def load_model(self, model_path: str):
        # Load model.
        pass

    def embed_sentence(self, query_string: str) -> list:
        # Should rerturns np.shape as (vector_size, )
        # Vector dimension will be detected by automatically.
        # 'self.lang' argument is only for Korean sentence preprocessing.
        pass

    def __del__(self):
        pass

    def __exit__(self):
        pass
