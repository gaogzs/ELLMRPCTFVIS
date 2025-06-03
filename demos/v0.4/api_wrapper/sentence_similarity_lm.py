from sentence_transformers import SentenceTransformer, util

class SentenceSimilarityWorker:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def cosine_similarity(self, sentence1, sentence2):
        embeddings1 = self.model.encode(sentence1, convert_to_tensor=True)
        embeddings2 = self.model.encode(sentence2, convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(embeddings1, embeddings2)
        return similarity.item()