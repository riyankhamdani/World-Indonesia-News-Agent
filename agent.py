import os
import requests
from langchain_groq import ChatGroq

# Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def search_tavily(query):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": 3,
        "search_depth": "basic"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:250]} for r in results]
        return []
    except Exception as e:
        print(f"Error searching '{query}': {e}")
        return []

def get_latest_news():
    queries = {
        "WORLD": "top global news headlines geopolitics world economy today",
        "INDONESIA": "berita utama indonesia terkini politik ekonomi isu nasional hari ini",
        "TECH": "latest global tech news artificial intelligence breakthrough today"
    }
    
    news_data = {}
    print("🔎 Searching global and national news...")
    for category, q in queries.items():
        news_data[category] = search_tavily(q)
        
    return news_data

def summarize_with_groq(news_data):
    print("🤖 AI summarizing news with Groq Llama 3.3...")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.2, api_key=GROQ_API_KEY)
    
    prompt = f"""
    You are a professional News Analyst for Riyan.
    Summarize the following raw search news into a clean, engaging daily digest in Bahasa Indonesia.

    RAW NEWS DATA:
    {news_data}

    INSTRUCTIONS:
    1. Group the report into 3 sections:
       - 🌐 **ISU GLOBAL & GEOPOLITIK** (2 berita utama dunia)
       - 🇮🇩 **ISU NASIONAL INDONESIA** (2 berita utama Indonesia)
       - 💻 **TECH & AI GLOBAL** (1-2 berita tech paling menarik)
    2. For each news item, give a title, a short 2-sentence summary explaining WHY it matters, and the source URL.
    3. Keep it objective, clear, concise, and easy to read on mobile.
    4. DO NOT use fancy Markdown tables or markdown symbols that break telegram. Use plain text formatting.

    Format template:
    DAILY NEWS DIGEST FOR RIYAN
    ====================================

    🌐 ISU GLOBAL & GEOPOLITIK
    • [Judul Berita]
      Summary: [Penjelasan ringkas]
      Link: [URL]

    🇮🇩 ISU NASIONAL INDONESIA
    • [Judul Berita]
      Summary: [Penjelasan ringkas]
      Link: [URL]

    💻 TECH & AI GLOBAL
    • [Judul Berita]
      Summary: [Penjelasan ringkas]
      Link: [URL]
    """
    
    try:
        report = llm.invoke(prompt).content
        return report
    except Exception as e:
        print(f"Summarizer Error: {e}")
        return "Gagal membuat rangkuman berita hari ini."

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print("🚀 News Digest successfully sent to Telegram!")
    else:
        print(f"❌ Telegram Send Failed: {res.text}")

if __name__ == "__main__":
    raw_news = get_latest_news()
    summary = summarize_with_groq(raw_news)
    send_telegram(summary)
