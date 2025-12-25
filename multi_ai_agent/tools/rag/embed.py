from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from typing import List

class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:

        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()

embedding_model_instance = SentenceTransformerEmbeddings("BAAI/bge-large-en-v1.5")
