import os
import requests
import telebot
from datetime import datetime
from langchain_groq import ChatGroq

# Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def search_tavily(query):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "topic": "news",
        "days": 1,
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
                is_specific = any(char.isdigit() for char in link) or "-" in link.split("/")[-1]
                if is_specific and len(link.split("/")) > 3:
                    valid_articles.append({"title": r.get("title"), "url": link, "snippet": r.get("content", "")[:300]})
            return valid_articles[:2] if valid_articles else [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]} for r in results[:2]]
        return []
    except Exception as e:
        return []

def get_news_digest():
    today_str = datetime.now().strftime("%B %d, %Y")
    queries = {
        "WORLD": f"breaking news geopolitics world economy today {today_str}",
        "INDONESIA": f"berita utama nasional indonesia politik ekonomi hari ini {today_str}",
        "TECH": f"latest artificial intelligence tech news breakthrough {today_str}"
    }
    news_data = {cat: search_tavily(q) for cat, q in queries.items()}
    
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1, api_key=GROQ_API_KEY)
    prompt = f"""
    You are Riyan's News Assistant. Summarize into Bahasa Indonesia:
    RAW NEWS: {news_data}
    
    Format:
    📰 **DAILY NEWS DIGEST** 📰
    ====================================
    🌐 **ISU GLOBAL & GEOPOLITIK**
    • [Judul]
      [Ringkasan 1 kalimat]
      🔗 Baca selengkapnya: [URL]

    🇮🇩 **ISU NASIONAL INDONESIA**
    • [Judul]
      [Ringkasan 1 kalimat]
      🔗 Baca selengkapnya: [URL]

    💻 **TECH & AI GLOBAL**
    • [Judul]
      [Ringkasan 1 kalimat]
      🔗 Baca selengkapnya: [URL]
    """
    return llm.invoke(prompt).content

# --- LISENER PESAN (INTERAKTIF KAYAK USER) ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Halo! Gue Riyan News Agent Bot 🤖\nKetik 'berita' atau /news buat dapet rangkuman berita terbaru hari ini ya!")

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    text = message.text.lower()
    
    if "berita" in text or "news" in text:
        bot.reply_to(message, "🔎 Bentar ya, lagi nyariin berita paling fresh hari ini...")
        report = get_news_digest()
        bot.send_message(message.chat.id, report, disable_web_page_preview=True)
    elif "riyan" in text or "oi" in text:
        bot.reply_to(message, "Halo! Riyan-nya lagi rehat/shift malam nih 😴 Kalo mau tau info berita hari ini, ketik 'berita' aja ya!")
    else:
        bot.reply_to(message, "Ketik 'berita' kalau mau dapet update berita terbaru hari ini ya! 😉")

if __name__ == "__main__":
    print("🤖 Bot interaktif siap melayani cewek lu 24/7...")
    bot.infinity_polling()
