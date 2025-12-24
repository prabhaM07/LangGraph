from crewai import Agent
from tools import yt_tool
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv

load_dotenv()

import os
# llm = ChatGroq(
#         model="llama-3.1-8b-instant",
#         groq_api_key=os.getenv("GROQ_API_KEY"),
#         temperature=0,
#         max_tokens=2000,
#         timeout=30,
#         max_retries=2,
#     )

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.8,
    timeout=30,
    max_retries=2,
)

## create a senior blog content researcher


blog_researcher = Agent(
  role = 'Blog Reseacher from Youtube Vedios',
  goal = 'get the relevant vedio content for the topic {topic} for YT channel',
  verbose = True,
  memory = True,
  backstory = (
    "Expert in understanding videos in AI Data Science , MAchine Learning And GEN AI and providing suggestion"
  ),
  tools=[yt_tool],
  llm=llm,
  allow_delegation=True
)


## creating a senior blog writer agent with YT tool

blog_writer=Agent(
    role='Blog Writer',
    goal='Narrate compelling tech stories about the video {topic} from YT video',
    verbose=True,
    memory=True,
    backstory=(
        "With a flair for simplifying complex topics, you craft"
        "engaging narratives that captivate and educate, bringing new"
        "discoveries to light in an accessible manner."
    ),
    tools=[yt_tool],
    llm=llm,
    allow_delegation=False
)

