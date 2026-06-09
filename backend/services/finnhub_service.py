import os
import requests

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

TOPICS = {
    "big-tech-capex": [
        "capex", "capital expenditure", "data center", "cloud infrastructure",
        "nvidia", "microsoft", "amazon", "google", "meta", "oracle"
    ],
    "agentic-ai": [
        "agentic ai", "ai agent", "autonomous agent", "copilot",
        "openai", "anthropic", "workflow automation", "enterprise ai"
    ]
}

def fetch_market_news():
    url = "https://finnhub.io/api/v1/news"

    response = requests.get(
        url,
        params={
            "category": "general",
            "token": FINNHUB_API_KEY
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()


def filter_news_by_topic(topic):
    articles = fetch_market_news()
    keywords = TOPICS.get(topic, [])

    filtered = []

    for article in articles:
        text = f"""
        {article.get("headline", "")}
        {article.get("summary", "")}
        {article.get("related", "")}
        """.lower()

        if any(keyword.lower() in text for keyword in keywords):
            filtered.append(article)

    return filtered[:12]