from flask import Blueprint, jsonify
from services.finnhub_service import filter_news_by_topic

news_bp = Blueprint("news", __name__)

@news_bp.get("/<topic>")
def get_topic_news(topic):
    try:
        articles = filter_news_by_topic(topic)
        return jsonify(articles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500