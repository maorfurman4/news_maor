import os
import requests
import json
from datetime import datetime, timedelta

# =============================================================================
# ─── הגדרות וסודות ───────────────────────────────────────────────────────────
# =============================================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN_NEWS")
CHAT_ID = os.environ.get("CHAT_ID_NEWS")

COMPANIES = ["Mobileye", "Intel", "Tesla", "Amazon", "D-Wave", "Klarna", "Grab", "Google", "Teva", "Supernus", "Novo Nordisk", "ASPI"]

# =============================================================================
# ─── פונקציות עזר ────────────────────────────────────────────────────────────
# =============================================================================
def fetch_news(query: str, language: str = "en") -> list:
    """מושך את הכתבות הכי חמות מ-NewsAPI מה-24 שעות האחרונות בלבד"""
    # חישוב התאריך של אתמול כדי למנוע חדשות ממוחזרות
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # שינוי משמעותי: הוספנו from=yesterday ושינינו את המיון ל-popularity (פופולריות יומית)
    url = f"https://newsapi.org/v2/everything?q={query}&from={yesterday}&sortBy=popularity&language={language}&apiKey={NEWS_API_KEY}"
    
    try:
        response = requests.get(url)
        # לוקחים 12 כתבות כדי לתת ל-AI מבחר טוב של חומר טרי
        articles = response.json().get("articles", [])[:12]
        
        clean_articles = []
        for a in articles:
            # סינון כתבות ללא כותרת או קישור (לפעמים ה-API מחזיר זבל)
            if a.get("title") and a.get("url") and a.get("title") != "[Removed]":
                clean_articles.append({
                    "title": a.get("title"),
                    "description": a.get("description"),
                    "source": a.get("source", {}).get("name"),
                    "url": a.get("url")
                })
        return clean_articles
    except Exception as e:
        print(f"❌ Error fetching news for '{query}': {e}")
        return []

def generate_analyst_brief(israel, ai, world, stocks) -> str:
    """שולח ל-GPT ומבקש פלט בפורמט HTML בטוח לטלגרם"""
    date_today = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    אתה "סוכן אנליסט" אישי ויוקרתי. תפקידך לכתוב בריף בוקר למנהל בכיר.
    קבל את רשימת החדשות הגולמיות באנגלית. *כל החדשות הן מה-24 שעות האחרונות.*
    המטרה שלך היא לייצר סיכום סופר-מעניין, קריא ומושך לעין.

    חוקי תוכן ועיצוב (HTML בלבד!):
    1. בחר בדיוק את 3 הכתבות הכי חשובות מכל קטגוריה, ותרגם לעברית.
    2. השתמש בתגיות HTML בסיסיות: <b> לטקסט מודגש, <i> לטקסט נטוי, ו-<a href="..."> לקישורים. אל תשתמש ב-Markdown (כמו כוכביות **).
    3. שים אימוג'י ייחודי שקשור לנושא ליד כל כותרת.

    לגבי "מעקב חברות": חפש דיווחים על החברות: {COMPANIES}. 
    אם יש חדשות, כתוב אותן. אם אין, כתוב: "💤 <i>אין דיווחים חריגים הבוקר לחברות במעקב.</i>"

    המידע הגולמי:
    ישראל: {israel}
    בינה מלאכותית: {ai}
    אקטואליה עולמית: {world}
    חברות ושוק ההון: {stocks}

    החזר את התשובה *בדיוק* בפורמט ה-HTML הבא (ללא בלוקים של קוד ```html):

    🌅 <b>בריף בוקר מנהלים - {date_today}</b> ☕

    🇮🇱 <b>ישראל</b>
    🔻 <b>[אימוג'י] [כותרת הכתבה]</b>
    💡 <i>השורה התחתונה:</i> [הסבר קצר, חד ומעניין ב-2 שורות]
    🔗 <a href="URL">לקריאת הכתבה המלאה</a>
    
    [שורה ריקה]
    
    🤖 <b>בינה מלאכותית (AI)</b>
    ...
    🌍 <b>אקטואליה עולמית</b>
    ...
    📈 <b>מעקב חברות ותיק מניות</b>
    ...
    """

    try:
        if not OPENAI_API_KEY:
            return "שגיאה: חסר מפתח OpenAI."

        url = "[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        }
        
        print("🧠 Sending request to OpenAI...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            return f"שגיאה ב-OpenAI: {response.status_code}"

        content = response.json()['choices'][0]['message']['content'].strip()
        # הסרת בלוקים של קוד אם ה-AI בטעות הוסיף אותם
        if content.startswith("```html"):
            content = content.replace("```html", "").replace("```", "").strip()
            
        return content
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return "שגיאה קריטית ביצירת הבריף."

def send_to_telegram(text: str):
    """שולח את הבריף המעוצב לטלגרם בפורמט HTML"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": CHAT_ID.strip(),
        "text": text,
        "parse_mode": "HTML", # הוחלף ל-HTML ליציבות מקסימלית
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Brief sent to Telegram successfully!")
        else:
            print(f"⚠️ Telegram API issue: {response.text}")
    except Exception as e:
        print(f"❌ Error sending to Telegram: {e}")

# =============================================================================
# ─── MAIN EXECUTION ──────────────────────────────────────────────────────────
# =============================================================================
if __name__ == "__main__":
    print("🚀 Starting Daily Briefing Analyst Agent...")
    
    print("📥 Fetching news from the last 24 hours...")
    israel_news = fetch_news("Israel economy OR Israel news")
    ai_news = fetch_news("Artificial Intelligence OR OpenAI OR Tech")
    world_news = fetch_news("Global Economy OR Geopolitics OR US Markets")
    
    companies_query = " OR ".join([f'"{company}"' for company in COMPANIES])
    stocks_news = fetch_news(f"({companies_query}) AND (stocks OR earnings OR market)")

    print("🧠 Analyzing and formatting...")
    briefing = generate_analyst_brief(israel_news, ai_news, world_news, stocks_news)
    
    print("📤 Sending to Telegram...")
    send_to_telegram(briefing)
    print("🏁 Run complete.")
