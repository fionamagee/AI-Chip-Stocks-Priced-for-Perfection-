import { useEffect, useState } from "react";
import { getNewsByTopic } from "../api/newsApi";
import "../styles/news.css";

const topics = [
  {
    id: "big-tech-capex",
    label: "Big Tech CapEx",
    description: "Data centers, chips, cloud infrastructure, and AI spending."
  },
  {
    id: "agentic-ai",
    label: "Shift to Agentic AI",
    description: "AI agents, copilots, automation, and enterprise AI workflows."
  }
];

export default function NewsSection() {
  const [selectedTopic, setSelectedTopic] = useState("big-tech-capex");
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadNews() {
      setLoading(true);

      try {
        const data = await getNewsByTopic(selectedTopic);
        setArticles(data);
      } catch (error) {
        console.error(error);
        setArticles([]);
      } finally {
        setLoading(false);
      }
    }

    loadNews();
  }, [selectedTopic]);

  const selectedTopicInfo = topics.find((topic) => topic.id === selectedTopic);

  return (
    <section className="news-section">
      <div className="news-header">
        <p className="eyebrow">Market Intelligence</p>
        <h1>AI & Big Tech News Tracker</h1>
        <p>{selectedTopicInfo.description}</p>
      </div>

      <div className="topic-tabs">
        {topics.map((topic) => (
          <button
            key={topic.id}
            className={selectedTopic === topic.id ? "active" : ""}
            onClick={() => setSelectedTopic(topic.id)}
          >
            {topic.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="loading">Loading news...</p>
      ) : (
        <div className="news-grid">
          {articles.map((article) => (
            <a
              href={article.url}
              target="_blank"
              rel="noreferrer"
              className="news-card"
              key={article.id}
            >
              {article.image && (
                <img src={article.image} alt={article.headline} />
              )}

              <div className="news-card-content">
                <span className="source">{article.source}</span>
                <h2>{article.headline}</h2>
                <p>{article.summary}</p>
              </div>
            </a>
          ))}
        </div>
      )}
    </section>
  );
}