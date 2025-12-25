import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

def get_llm():
    """Initialize and return LLM instance"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    return ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=api_key,
        temperature=0,
        max_tokens=2000,
        timeout=30,
        max_retries=2,
    )