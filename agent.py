import os
import sys
import requests
import telebot
from datetime import datetime
from langchain_groq import ChatGroq

# Environment Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Inisialisasi Bot secara aman
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

def search_tavily(query):
    """Mencari berita terbaru menggunakan Tavily Search API."""
    if not TAVILY_API_KEY:
        print("⚠️ Warning: TAVILY_API_KEY tidak ditemukan.")
        return []

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
                    valid_articles.append({
                        "title": r.get("title", "Berita Tanpa Judul"),
                        "url": link,
                        "snippet": r.get("content", "")[:300]
                    })
            if valid_articles:
                return valid_articles[:2]
            return [
                {
                    "title": r.get("title", "Berita Tanpa Judul"),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:300]
                } for r in results[:2]
            ]
        else:
            print(f"❌ Tavily Error status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching news from Tavily: {e}")
        return []

def get_news_digest():
    """Mengambil berita & merangkumnya menggunakan Groq LLaMA 3.1 Instant."""
    today_str = datetime.now().strftime("%B %d, %Y")
    queries = {
        "WORLD": f"breaking news geopolitics world economy today {today_str}",
        "INDONESIA": f"berita utama nasional indonesia politik ekonomi hari ini {today_str}",
        "TECH": f"latest artificial intelligence tech news breakthrough {today_str}"
    }
    news_data = {cat: search_tavily(q) for cat, q in queries.items()}
    
    if not GROQ_API_KEY:
        return "❌ Error: GROQ_API_KEY belum dikonfigurasi."

    try:
        # Menggunakan model llama-3.1-8b-instant yang dijamin aktif & anti-decommission di Groq
        llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            temperature=0.1,
            api_key=GROQ_API_KEY
        )
        prompt = f"""
You are Riyan's News Assistant. Summarize into natural, concise Bahasa Indonesia.
RAW NEWS: {news_data}

Instructions:
1. Return ONLY the formatted message below.
2. Ensure links are included and valid.
3. Keep summaries clear and to the point (1-2 sentences per item).

Format:
📰 **DAILY NEWS DIGEST** 📰
====================================

🌐 **ISU GLOBAL & GEOPOLITIK**
• [Judul]
  [Ringkasan 1-2 kalimat]
  🔗 Baca selengkapnya: [URL]

🇮🇩 **ISU NASIONAL INDONESIA**
• [Judul]
  [Ringkasan 1-2 kalimat]
  🔗 Baca selengkapnya: [URL]

💻 **TECH & AI GLOBAL**
• [Judul]
  [Ringkasan 1-2 kalimat]
  🔗 Baca selengkapnya: [URL]
"""
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"❌ Error generating summary with LLM: {e}")
        raise e

# --- HANDLER INTERAKTIF (Untuk mode Server/Polling 24/7) ---
if bot:
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(
            message,
            "Halo! Gue Riyan News Agent Bot 🤖\n\n"
            "Ketik 'berita' atau /news buat dapet rangkuman berita terbaru hari ini ya!"
        )

    @bot.message_handler(commands=['news'])
    def send_news_command(message):
        bot.reply_to(message, "🔎 Bentar ya, lagi nyariin berita paling fresh hari ini...")
        try:
            report = get_news_digest()
            send_safe_message(message.chat.id, report)
        except Exception:
            send_safe_message(message.chat.id, "⚠️ Gagal membuat rangkuman berita. Kemungkinan API Key Groq bermasalah. Silakan coba beberapa saat lagi.")

    @bot.message_handler(func=lambda msg: True)
    def handle_all_messages(message):
        text = message.text.lower() if message.text else ""
        
        if "berita" in text or "news" in text:
            bot.reply_to(message, "🔎 Bentar ya, lagi nyariin berita paling fresh hari ini...")
            try:
                report = get_news_digest()
                send_safe_message(message.chat.id, report)
            except Exception:
                send_safe_message(message.chat.id, "⚠️ Gagal membuat rangkuman berita. Kemungkinan API Key Groq bermasalah. Silakan coba beberapa saat lagi.")
        elif "riyan" in text or "oi" in text or text.strip() == "p":
            bot.reply_to(message, "Halo! Riyan-nya lagi rehat/shift malam nih 😴 Kalo mau tau info berita hari ini, ketik 'berita' aja ya!")
        else:
            bot.reply_to(message, "Ketik 'berita' kalau mau dapet update berita terbaru hari ini ya! 😉")

def send_safe_message(chat_id, text):
    """Mengirim pesan dengan fallback aman jika Markdown error."""
    if not bot:
        print("❌ Bot instance tidak ditemukan.")
        return
    try:
        bot.send_message(chat_id, text, disable_web_page_preview=True, parse_mode="Markdown")
    except Exception as e:
        print(f"⚠️ Gagal kirim via Markdown ({e}). Mencoba kirim teks biasa...")
        bot.send_message(chat_id, text, disable_web_page_preview=True)

# --- PENENTU MODE EKSEKUSI ---
if __name__ == "__main__":
    is_cron_mode = "--cron" in sys.argv or os.getenv("RUN_MODE") == "cron"

    if is_cron_mode:
        print("🚀 Menjalankan Bot dalam MODE CRON (GitHub Actions)...")
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Error: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diset di secrets.")
            sys.exit(1)
            
        print("🔎 Mengambil dan merangkum berita...")
        try:
            report = get_news_digest()
            print(f"📤 Mengirim pesan ke Chat ID: {TELEGRAM_CHAT_ID}...")
            send_safe_message(TELEGRAM_CHAT_ID, report)
            print("✅ Berhasil dikirim! Selesai.")
        except Exception:
            print("❌ Gagal membuat rangkuman berita.")
            sys.exit(1)
    else:
        print("🤖 Bot interaktif siap melayani 24/7 (Mode Polling)...")
        if bot:
            bot.infinity_polling()
        else:
            print("❌ Error: TELEGRAM_BOT_TOKEN tidak dikonfigurasi.")
