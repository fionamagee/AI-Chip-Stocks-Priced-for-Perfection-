const API_BASE = "http://127.0.0.1:5000/api/news";

export async function getNewsByTopic(topic) {
  const response = await fetch(`${API_BASE}/${topic}`);

  if (!response.ok) {
    throw new Error("Failed to fetch news");
  }

  return response.json();
}