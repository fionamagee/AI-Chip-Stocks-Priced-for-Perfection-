from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from routes.news import news_bp

load_dotenv()

app = Flask(__name__)

CORS(app)

app.register_blueprint(news_bp, url_prefix="/api/news")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)