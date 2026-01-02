import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROK_API_KEY"),
        temperature=0.7,
        max_tokens=800,
        timeout=30,
        max_retries=2,
    )
    