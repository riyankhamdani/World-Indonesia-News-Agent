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
        "max_results": 4,
        "search_depth": "advanced", # Pake advanced biar dapet deep link artikel
        "include_domains": []
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            
            # Saring HANYA link spesifik (yang punya path/slug panjang, bukan cuma domain utama)
            valid_articles = []
            for r in results:
                link = r.get("url", "")
                # Minimal ada path artikel (misal ada slash setelah domain)
                if link.count("/") >= 4 or ".html" in link or "-" in link.split("/")[-1]:
                    valid_articles.append({
                        "title": r.get("title"),
                        "url": link,
                        "snippet": r.get("content", "")[:300]
                    })
            
            # Kalo penyeleksian ketat dapet hasil, pake itu. Kalo gak, pake default results
            return valid_articles if valid_articles else [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]} for r in results]
        return []
    except Exception as e:
        print(f"Error searching '{query}': {e}")
        return []

def get_latest_news():
    # Query dibuat lebih spesifik ke peristiwa hari ini biar dapet artikel spesifik
    queries = {
        "WORLD": "breaking news world politics economy world today site:reuters.com OR site:apnews.com OR site:bbc.com",
        "INDONESIA": "berita hari ini nasional politik ekonomi site:detik.com OR site:kompas.com OR site:cnnindonesia.com",
        "TECH": "latest artificial intelligence tech news article today site:techcrunch.com OR site:theverge.com"
    }
    
    news_data = {}
    print("🔎 Searching specific article links...")
    for category, q in queries.items():
        news_data[category] = search_tavily(q)
        
    return news_data

def summarize_with_groq(news_data):
    print("🤖 AI summarizing news with Groq Llama 3.3...")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1, api_key=GROQ_API_KEY)
    
    prompt = f"""
    You are a professional News Analyst for Riyan.
    Summarize the following raw search news into a clean daily digest in Bahasa Indonesia.

    RAW NEWS DATA:
    {news_data}

    INSTRUCTIONS:
    1. Group the report into 3 sections:
       - 🌐 ISU GLOBAL & GEOPOLITIK (2 berita)
       - 🇮🇩 ISU NASIONAL INDONESIA (2 berita)
       - 💻 TECH & AI GLOBAL (1-2 berita)
    2. For each item, display:
       - Title
       - 2-sentence summary
       - The EXACT URL provided in the RAW DATA.
    3. ABSOLUTE RULE FOR LINKS: Do NOT edit, truncate, or invent any URL. Copy the exact "url" string from the raw data.

    Format template:
    📰 DAILY NEWS DIGEST FOR RIYAN 📰
    ====================================

    🌐 ISU GLOBAL & GEOPOLITIK
    • [Judul Berita]
      Summary: [Penjelasan ringkas 2 kalimat]
      🔗 Link: [EXACT_URL_FROM_DATA]

    🇮🇩 ISU NASIONAL INDONESIA
    • [Judul Berita]
      Summary: [Penjelasan ringkas 2 kalimat]
      🔗 Link: [EXACT_URL_FROM_DATA]

    💻 TECH & AI GLOBAL
    • [Judul Berita]
      Summary: [Penjelasan ringkas 2 kalimat]
      🔗 Link: [EXACT_URL_FROM_DATA]
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
