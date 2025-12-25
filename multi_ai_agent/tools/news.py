import feedparser
from langchain_core.tools import tool

@tool
def get_travel_news(destination: str = "") -> str:
    """Get latest travel news, optionally filtered by destination.
    
    Args:
        destination: Optional destination name to filter news (e.g., 'India', 'Thailand', 'Europe'). 
                    Leave empty for general travel news.
    
    Returns:
        Latest travel news articles with titles, links, and summaries
    """
    travel_feeds = {
        "nytimes_travel": "https://rss.nytimes.com/services/xml/rss/nyt/Travel.xml",
        "lonely_planet": "https://www.lonelyplanet.com/news/feed",
    }
    
    all_articles = []
    
    for source, feed_url in travel_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Get more entries initially
                all_articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', 'N/A'),
                    'summary': entry.get('summary', '')[:300],
                    'source': source
                })
        except Exception as e:
            continue
    
    # Filter by destination if provided
    if destination:
        filtered = [
            article for article in all_articles
            if destination.lower() in article['title'].lower() 
            or destination.lower() in article['summary'].lower()
        ]
        # If no matches found, return general news with a note
        if not filtered:
            result = f"No specific news found for {destination}. Here's recent general travel news:\n\n"
        else:
            all_articles = filtered
            result = f"Travel News about {destination}:\n\n"
    else:
        result = "Latest Travel News:\n\n"
    
    if not all_articles:
        return "Unable to retrieve travel news at this time. Please try again later."
    
    for i, article in enumerate(all_articles[:5], 1):
        result += f"{i}. {article['title']}\n"
        result += f"   Source: {article['source']} | {article['published']}\n"
        result += f"   Summary: {article['summary']}\n"
        result += f"   Link: {article['link']}\n\n"
    
    return result
