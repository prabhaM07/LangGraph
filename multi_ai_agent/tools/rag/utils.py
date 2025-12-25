from langchain_core.documents import Document
from typing import List

def flatten_chunks(agentic_chunks: List[List[Document]]) -> List[Document]:
    flattened = []
    for chunk_group in agentic_chunks:
        flattened.extend(chunk_group)
    return flattened
  

def format_context(documents: List[Document]) -> str:
    """Format retrieved documents into context string with metadata"""
    context_parts = []
    for i, doc in enumerate(documents, 1):
        # Extract metadata
        metadata = doc.metadata
        filename = metadata.get('filename', 'N/A')
        source = metadata.get('source', 'Unknown')
        
        # Format header with metadata
        context_parts.append(f"[Document {i} - filename: {filename}, Source: {source}]")
        context_parts.append(doc.page_content)
        context_parts.append("") 
    return "\n".join(context_parts)