import os
import requests
from datetime import datetime
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
        "topic": "news",
        "days": 1,                 # Mengunci berita 24 jam terakhir
        "max_results": 5,
        "search_depth": "advanced"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            
            valid_articles = []
            for r in results:
                link = r.get("url", "")
                is_specific_url = any(char.isdigit() for char in link) or "-" in link.split("/")[-1] or ".html" in link
                
                if is_specific_url and len(link.split("/")) > 3:
                    valid_articles.append({
                        "title": r.get("title"),
                        "url": link,
                        "snippet": r.get("content", "")[:300]
                    })
            
            return valid_articles[:2] if valid_articles else [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]} for r in results[:2]]
        return []
    except Exception as e:
        print(f"Error searching '{query}': {e}")
        return []

def get_latest_news():
    today_str = datetime.now().strftime("%B %d, %Y")
    
    queries = {
        "WORLD": f"breaking news geopolitics world economy today {today_str}",
        "INDONESIA": f"berita utama nasional indonesia politik ekonomi hari ini {today_str}",
        "TECH": f"latest artificial intelligence tech news breakthrough {today_str}"
    }
    
    news_data = {}
    print(f"🔎 Searching fresh news for {today_str}...")
    for category, q in queries.items():
        news_data[category] = search_tavily(q)
        
    return news_data

def summarize_with_groq(news_data):
    print("🤖 AI generating minimal digest with Groq Llama 3.3...")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1, api_key=GROQ_API_KEY)
    
    prompt = f"""
    You are a professional News Digest Assistant for Riyan.
    Create a VERY SHORT, ULTRA-CONCISE news summary in Bahasa Indonesia from the raw data.

    RAW NEWS DATA:
    {news_data}

    INSTRUCTIONS:
    1. Group into 3 sections:
       - 🌐 **ISU GLOBAL & GEOPOLITIK**
       - 🇮🇩 **ISU NASIONAL INDONESIA**
       - 💻 **TECH & AI GLOBAL**
    2. For each news item, output ONLY:
       - Bold Title
       - 1 short, catchy sentence summary (max 15 words)
       - Link to full article
    3. Keep it minimal so Riyan can scan in 10 seconds and click the link if curious.
    4. ABSOLUTE RULE FOR URL: Copy the exact full "url" string provided in the raw data without changing anything.

    Format template:
    📰 **DAILY NEWS DIGEST** 📰
    ====================================

    🌐 **ISU GLOBAL & GEOPOLITIK**
    • [Judul Berita]
      [Ringkasan 1 kalimat singkat]
      🔗 Baca selengkapnya: [EXACT_URL_FROM_DATA]

    🇮🇩 **ISU NASIONAL INDONESIA**
    • [Judul Berita]
      [Ringkasan 1 kalimat singkat]
      🔗 Baca selengkapnya: [EXACT_URL_FROM_DATA]

    💻 **TECH & AI GLOBAL**
    • [Judul Berita]
      [Ringkasan 1 kalimat singkat]
      🔗 Baca selengkapnya: [EXACT_URL_FROM_DATA]
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
        print("🚀 Compact News Digest successfully sent to Telegram!")
    else:
        print(f"❌ Telegram Send Failed: {res.text}")

if __name__ == "__main__":
    raw_news = get_latest_news()
    summary = summarize_with_groq(raw_news)
    send_telegram(summary)
