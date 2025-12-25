import re
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain.messages import SystemMessage, HumanMessage


class Chunking:
    
    def chunking_1(self, chunk_size: int, chunk_overlap: int, docs: List[Document], 
                   separators: List[str] = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators
        )
        return splitter.split_documents(docs)

    def chunking_3(self, llm: ChatGroq, doc: Document):
        system_prompt = """Improve this text by:
- Fixing grammar and spelling errors
- Making sentences clear and meaningful
- Ensuring proper context and flow
- Keeping the same information and length

Return ONLY the corrected text, no explanations or extra formatting."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=doc.page_content)
        ]
        
        try:
            response = llm.invoke(messages)
            corrected_text = response.content.strip()
            
            corrected_text = re.sub(r'^```.*?\n|```$', '', corrected_text, flags=re.MULTILINE).strip()
            
            print(f"✓ Corrected chunk (length: {len(corrected_text)})\n")
            
            return Document(
                page_content=corrected_text,
                metadata={**doc.metadata, "corrected": True}
            )
            
        except Exception as e:
            print(f"⚠ Error correcting text: {e}. Using original.\n")
            return Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "corrected": False}
            )
            
            