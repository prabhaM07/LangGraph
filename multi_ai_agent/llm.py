import os
from langchain_groq import ChatGroq

def get_llm():
    
    return ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_tokens=2000,
        timeout=30,
        max_retries=2,
    )

