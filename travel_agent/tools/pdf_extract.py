import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer

from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from typing import List



load_dotenv()

# ---------- LLM ----------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=500,
    timeout=30,
)

# ---------- SentenceTransformer Embeddings ----------
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(
            texts,
            convert_to_tensor=False,
            show_progress_bar=False
        ).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(
            text,
            convert_to_tensor=False
        ).tolist()


embeddings = SentenceTransformerEmbeddings()

# ---------- PDF → VectorStore ----------
def load_pdf_vectorstore(pdf_path: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)

    return FAISS.from_documents(chunks, embeddings)

# ---------- Tool ----------
@tool
def extract_from_pdf(question: str) -> str:
    """
    Answer questions using the travel PDF.
    """
    try:
        pdf_path = r"D:\materials\LANGGRAPH\projects\travel_agent\travel.pdf"

        vectorstore = load_pdf_vectorstore(pdf_path)

        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        docs = retriever.invoke(question)

        if not docs:
            return "No relevant information found in the PDF."

        context = "\n\n".join(doc.page_content for doc in docs)

        prompt = f"""
You are answering using a travel guide.

Context:
{context}

Question:
{question}

Answer concisely and factually.
"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"Error: {str(e)}"
