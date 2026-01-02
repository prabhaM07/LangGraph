from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


class PDFLoader:
  
  def load_pdf(self,pdf_path : str):
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
      raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    loader = PyPDFLoader(pdf_path)
    
    documents = loader.load()
    
    for i,doc in enumerate(documents):
      doc.metadata.update(
        {
          "chunk_id" :i,
          "source":str(pdf_path)
        }
      )

    return documents
  
  def load_directory(self, pdf_dir: str):

        pdf_dir = Path(pdf_dir)

        if not pdf_dir.exists():
            raise FileNotFoundError(f"Directory not found: {pdf_dir}")

        all_docs: List[Document] = []

        for pdf_path in pdf_dir.glob("*.pdf"):
            docs = self.load_pdf(pdf_path)
            all_docs.extend(docs)

        return all_docs
  