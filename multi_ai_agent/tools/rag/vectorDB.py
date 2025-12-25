from langchain_chroma import Chroma
from tools.rag.embed import embedding_model_instance

vector_store = Chroma(
  collection_name="RAG_collection",
  embedding_function=embedding_model_instance,
  persist_directory="./chroma_rag_db",
)
