import feedparser
from langchain.tools import tool

@tool
def get_travel_news(destination: str = "") -> str:
    """Get travel news from specialized travel sources. Input can be empty or a destination name."""
    
    travel_feeds = {
        "nytimes_travel": "https://rss.nytimes.com/services/xml/rss/nyt/Travel.xml",
        "lonely_planet": "https://www.lonelyplanet.com/news/feed",
    }
    
    all_articles = []
    
    for source, feed_url in travel_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                all_articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', 'N/A'),
                    'summary': entry.get('summary', '')[:200],
                    'source': source
                })
        except Exception as e:
            continue
    
    if destination:
        all_articles = [
            article for article in all_articles
            if destination.lower() in article['title'].lower() 
            or destination.lower() in article['summary'].lower()
        ]
    
    if not all_articles:
        return f"No travel news found{' for ' + destination if destination else ''}."
    
    result = f"Travel News{' about ' + destination if destination else ''}:\n\n"
    for i, article in enumerate(all_articles[:5], 1):
        result += f"{i}. {article['title']}\n"
        result += f"   Source: {article['source']} | {article['published']}\n"
        result += f"   Link: {article['link']}\n\n"
    
    return result
