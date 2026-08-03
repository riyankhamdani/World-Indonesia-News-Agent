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
        "days": 1,                 # ⚡ KUNCI UTAMA: Cuma ambil berita 1 hari terakhir (24 jam)
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
    # Ambil tanggal hari ini secara otomatis (Format: August 03, 2026)
    today_str = datetime.now().strftime("%B %d, %Y")
    
    # Query disisipi tanggal hari ini biar tidak narik berita lama
    queries = {
        "WORLD": f"breaking news geopolitics world economy today {today_str}",
        "INDONESIA": f"berita utama nasional indonesia politik ekonomi hari ini {today_str}",
        "TECH": f"latest artificial intelligence tech news breakthrough {today_str}"
    }
    
    news_data = {}
    print(f"🔎 Searching news specifically for today ({today_str})...")
    for category, q in queries.items():
        news_data[category] = search_tavily(q)
        
    return news_data

def summarize_with_groq(news_data):
    print("🤖 AI summarizing news with Groq Llama 3.3...")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1, api_key=GROQ_API_KEY)
    
    prompt = f"""
    You are a professional News Analyst for Riyan.
    Summarize the following raw news data into a clean daily digest in Bahasa Indonesia.

    RAW NEWS DATA:
    {news_data}

    INSTRUCTIONS:
    1. Summarize into 3 categories:
       - 🌐 ISU GLOBAL & GEOPOLITIK
       - 🇮🇩 ISU NASIONAL INDONESIA
       - 💻 TECH & AI GLOBAL
    2. For each item, present:
       - Bold Title
       - 2-sentence summary explaining why it matters
       - The EXACT full URL provided in the raw data.
    3. CRITICAL: Only write summaries based on the raw data provided. Do not shorten or alter the URLs.

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
