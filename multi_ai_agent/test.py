# test_rag.py
import asyncio
from tools.rag.app import main_travel_query

async def test():
    pdf_path = 'D:\\materials\\LANGGRAPH\\projects\\multi_ai_agent\\travel.pdf'
    query = "I need to travel within India below 50000"
    result = await main_travel_query(pdf_path, query)
    print("RAW RAG OUTPUT:")
    print(result)
    print("\nOutput type:", type(result))

if __name__ == "__main__":
    asyncio.run(test())