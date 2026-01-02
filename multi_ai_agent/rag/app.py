import asyncio
import json
from pathlib import Path
import re
from typing import List, Optional


class DocumentProcessor:
    def __init__(self, pdf_path: Path, vector_store, persist_dir: Optional[Path] = None):
        self.pdf_path = pdf_path 
        self.vector_store = vector_store
        self.persist_dir = persist_dir
    
    def setup_sync(self):
        """Synchronous setup - to be called within asyncio.to_thread"""
        # Create default persist_dir if not provided
        if self.persist_dir is None:
            self.persist_dir = Path("./chroma_rag_db")
        
        # Blocking mkdir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_already_processed(self) -> bool:
        """Check if documents are already in vector store - synchronous"""
        try:
            collection_count = self.vector_store._collection.count()
            if collection_count > 0:
                print(f"✓ Found {collection_count} existing chunks in vector store")
                return True
            return False
        except:
            return False
    
    def _process_documents_sync(self):
        """Synchronous version - to be called within asyncio.to_thread"""
        # Lazy import
        from langchain_core.documents import Document
        from rag.load_pdf import PDFLoader
        from rag.chunking import Chunking
        from rag.llm import llm
        
        # Check if already processed
        if self._is_already_processed():
            print("Skipping document processing - using existing vector store")
            return self.vector_store._collection.count()
        
        print("Processing documents for the first time...")
        
        # All operations are now synchronous
        pdf_loader = PDFLoader() 
        docs = pdf_loader.load_pdf(pdf_path=self.pdf_path)
         
        chunker = Chunking() 
        recursive_chunks = chunker.chunking_1(docs=docs, chunk_size=1000, chunk_overlap=200)
      
        # Process chunks
        corrected_chunks: List[Document] = []
        for i, doc in enumerate(recursive_chunks):
            print(f"Processing chunk {i+1}/{len(recursive_chunks)}...", end="\r")
            corrected_doc = chunker.chunking_3(doc=doc, llm=llm)
            if corrected_doc is not None:
                corrected_chunks.append(corrected_doc)

        # Store in vector DB
        self.vector_store.add_documents(corrected_chunks)

        print(f"\n✓ Processed and stored {len(corrected_chunks)} chunks")
        print(f"✓ Vector store persisted to: {self.persist_dir}")
        return len(corrected_chunks)


class HybridRetriever:
    def __init__(self, retriever_vector_store, k: int = 3):
        self.vector_store = retriever_vector_store
        self.k = k
        self.merge_retriever = None
    
    def _setup_retrievers_sync(self):
        """Synchronous version - to be called within asyncio.to_thread"""
        # Lazy import
        from langchain_core.documents import Document
        from langchain_community.retrievers import BM25Retriever
        from langchain_classic.retrievers import MergerRetriever
        
        collection_count = self.vector_store._collection.count()
        
        if collection_count == 0:
            raise ValueError("Vector store is empty. Process documents first.")
        
        raw_docs = self.vector_store.get(include=["documents"])
      
        documents = [
            Document(page_content=doc)
            for doc in raw_docs["documents"]
        ]
        
        bm25_retriever = BM25Retriever.from_documents(documents=documents, k=self.k)

        similarity_search_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={'k': self.k}
        )
        
        print(f"Initialized retrievers with {len(documents)} documents")
        
        self.merge_retriever = MergerRetriever(
            retrievers=[similarity_search_retriever, bm25_retriever], 
            weights=[0.6, 0.4]
        )

    async def retrieve(self, user_query: str):
        if self.merge_retriever is None:
            raise ValueError("Retrievers not set up. Call _setup_retrievers() first.")
        
        # Move blocking invoke to thread
        retrieved_docs = await asyncio.to_thread(self.merge_retriever.invoke, user_query)
        return retrieved_docs


class TravelRecommendationGenerator:
    def __init__(self, retriever: HybridRetriever, llm):        
        self.retriever = retriever
        self.llm = llm
        self.output_parser = None
    
    async def generate_response(self, user_query: str):
        # Lazy import
        from langchain_core.output_parsers import StrOutputParser
        from langchain.messages import HumanMessage, SystemMessage
        from rag.utils import format_context
        
        if self.output_parser is None:
            self.output_parser = StrOutputParser()
        
        print(f"\n🔍 Retrieving documents for: {user_query}")
        retrieved_docs = await self.retriever.retrieve(user_query)
        print(f"✓ Retrieved {len(retrieved_docs)} documents\n")

        # Move format_context to thread in case it has blocking operations
        context = await asyncio.to_thread(format_context, retrieved_docs)
        
        system_prompt = """You are a knowledgeable travel advisor specializing in personalized destination recommendations.

Based on the travel catalog information provided, suggest destinations and packages that match the user's preferences.

Your recommendations should include:
- Destination names and highlights
- Key activities and experiences
- Accommodation types or package details
- Why these destinations match their interests

Be enthusiastic, descriptive, and helpful. If specific pricing or detailed package info is available, include it."""

        user_prompt = f"""
Context from travel catalog:
{context}

User's travel query: {user_query}

Based on the catalog information, provide personalized travel recommendations:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        chain = self.llm | self.output_parser
        
        result = await chain.ainvoke(messages)
        return result


# Global pipeline instance (singleton pattern)
_pipeline_instance = None


async def initialize_travel_pipeline(pdf_path: str, persist_dir: str = "./chroma_db", 
                                    force_reprocess: bool = False) -> TravelRecommendationGenerator:
    """
    Initialize the RAG pipeline once and reuse it.
    
    Args:
        pdf_path: Path to the PDF file
        persist_dir: Directory to persist vector store (default: ./chroma_db)
        force_reprocess: If True, reprocess documents even if they exist
    """
    global _pipeline_instance
    
    if _pipeline_instance is not None and not force_reprocess:
        print("Using existing pipeline instance")
        return _pipeline_instance
    
    # Wrap the entire initialization in a single thread
    def _init_pipeline():
        # Lazy import inside thread
        from rag.vectorDB import vector_store
        from rag.llm import llm
        
        # Create Path objects
        pdf_path_obj = Path(pdf_path)
        persist_dir_obj = Path(persist_dir)
        
        # Check if PDF exists
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path_obj}")
        
        # Clear vector store if force reprocess
        if force_reprocess:
            print("Force reprocessing enabled - clearing existing data...")
            try:
                vector_store.delete_collection()
                vector_store._collection = vector_store._client.get_or_create_collection(
                    name=vector_store._collection.name
                )
            except Exception as e:
                print(f"Warning: Could not reset collection: {e}")
        
        # Process documents (all synchronous now)
        processor = DocumentProcessor(pdf_path_obj, vector_store, persist_dir_obj)
        processor.setup_sync()
        chunk_count = processor._process_documents_sync()

        # Setup retrievers (synchronous)
        retriever = HybridRetriever(vector_store, k=3)
        retriever._setup_retrievers_sync()
        
        # Create generator
        generator = TravelRecommendationGenerator(retriever, llm)
        
        return generator
    
    # Run the entire initialization in a thread
    _pipeline_instance = await asyncio.to_thread(_init_pipeline)
    
    return _pipeline_instance


async def main_travel_query(pdf_path: str, user_query: str, 
                           persist_dir: str = "./chroma_db",
                           force_reprocess: bool = False):
    """
    Direct interface for getting travel recommendations.
    
    Args:
        pdf_path: Path to the PDF file
        user_query: User's travel query
        persist_dir: Directory to persist vector store
        force_reprocess: If True, reprocess documents even if they exist
    """
    try:
        generator = await initialize_travel_pipeline(
            pdf_path, persist_dir, force_reprocess
        )
        response = await generator.generate_response(user_query)
        
        print(f"\n{'='*60}")
        print("TRAVEL RECOMMENDATIONS")
        print(f"{'='*60}\n")
        print(response)
        print(f"\n{'='*60}\n")
        
        return response
        
    except Exception as e:
        print(f"Error in main_travel_query: {e}")
        import traceback
        traceback.print_exc()
        return None


async def clear_vector_store(persist_dir: str = "./chroma_db"):
    """
    Utility function to clear the persisted vector store.
    Use this when you want to force reprocessing of documents.
    """
    def _clear_sync():
        import shutil
        persist_path = Path(persist_dir)
        
        if persist_path.exists():
            shutil.rmtree(persist_path)
            print(f"✓ Cleared vector store at {persist_dir}")
        else:
            print(f"No vector store found at {persist_dir}")
    
    await asyncio.to_thread(_clear_sync)