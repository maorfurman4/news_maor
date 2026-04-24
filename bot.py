import os
import requests
import json
from datetime import datetime

# =============================================================================
# ─── הגדרות וסודות ───────────────────────────────────────────────────────────
# =============================================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN_NEWS")
CHAT_ID = os.environ.get("CHAT_ID_NEWS")

# רשימת החברות המדויקת שביקשת למעקב
COMPANIES = ["Mobileye", "Intel", "Tesla", "Amazon", "D-Wave", "Klarna", "Grab", "Google", "Teva", "Supernus", "Novo Nordisk", "ASPI"]

# =============================================================================
# ─── פונקציות עזר ────────────────────────────────────────────────────────────
# =============================================================================
def fetch_news(query: str, language: str = "en") -> list:
    """מושך את הכתבות הכי חמות מ-NewsAPI לפי שאילתה"""
    # אנחנו מביאים את ה-10 הכי רלוונטיות, כדי שה-AI יוכל לבחור את ה-3 הכי טובות מתוכן
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=relevancy&language={language}&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        articles = response.json().get("articles", [])[:10]
        
        # זיקוק המידע הרלוונטי כדי לחסוך בטוקנים ל-OpenAI
        clean_articles = []
        for a in articles:
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
    """שולח הכל ל-GPT-4o כדי שיערוך, יסנן ויתרגם לעברית ברמה גבוהה"""
    date_today = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    אתה "סוכן אנליסט" אישי ויוקרתי. תפקידך לכתוב בריף בוקר למנהל בכיר.
    קבל את רשימת החדשות הגולמיות באנגלית. עליך:
    1. לבחור בדיוק את 3 הכתבות הכי חשובות ומשמעותיות מכל קטגוריה.
    2. לתרגם אותן לעברית רהוטה, עסקית ומקצועית.
    3. לכתוב "בריף" של שורה-שתיים לכל כתבה שמסביר את השורה התחתונה.
    4. לצרף את הלינק המקורי לכל כתבה.

    לגבי "מעקב חברות": חפש בחדשות המצורפות אם יש משהו קריטי או דיווח פיננסי על החברות: {COMPANIES}. 
    אם יש חדשות, ציין זאת. אם לא, כתוב: "אין דיווחים חריגים הבוקר לחברות במעקב".

    המידע הגולמי:
    ישראל: {israel}
    בינה מלאכותית: {ai}
    אקטואליה עולמית: {world}
    חברות ושוק ההון: {stocks}

    החזר את התשובה בפורמט טקסט מעוצב לטלגרם.
    """

    try:
        # בדיקה אם המפתח בכלל קיים בגיטהאב
        if not OPENAI_API_KEY:
            print("❌ ERROR: OPENAI_API_KEY is missing! Did you add it to GitHub Secrets?")
            return "שגיאה: חסר מפתח OpenAI ב-Secrets של גיטהאב."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        print("🧠 Sending request to OpenAI...")
        response = requests.post(url, json=payload, headers=headers)
        
        # בדיקה מה הסטטוס שחזר מ-OpenAI
        if response.status_code != 200:
            print(f"❌ OpenAI API Error [{response.status_code}]: {response.text}")
            return f"שגיאה מול השרת של OpenAI. קוד שגיאה: {response.status_code}"

        return response.json()['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        print(f"❌ Critical Error parsing OpenAI response: {e}")
        return "שגיאה קריטית ביצירת הבריף. אנא בדוק את לוג המערכת."

def send_to_telegram(text: str):
    """שולח את הבריף המוכן לערוץ הטלגרם שלך"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": CHAT_ID.strip(),
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True # מבטל תצוגה מקדימה כדי שההודעה תיראה נקייה
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
# ─── MAIN EXECUTION (מנוע ההרצה) ─────────────────────────────────────────────
# =============================================================================
if __name__ == "__main__":
    print("🚀 Starting Daily Briefing Analyst Agent...")
    
    # 1. איסוף המידע מהעולם
    print("📥 Fetching Israel news...")
    israel_news = fetch_news("Israel economy OR Israel news")
    
    print("📥 Fetching AI news...")
    ai_news = fetch_news("Artificial Intelligence OR OpenAI OR GPT OR Tech")
    
    print("📥 Fetching World news...")
    world_news = fetch_news("Global Economy OR Geopolitics OR US Markets")
    
    print("📥 Fetching Companies news...")
    # בונה שאילתה חכמה שמחפשת ספציפית את החברות שלך
    companies_query = " OR ".join([f'"{company}"' for company in COMPANIES])
    stocks_news = fetch_news(f"({companies_query}) AND (stocks OR earnings OR market)")

    # 2. עיבוד, תרגום וסיכום על ידי AI
    print("🧠 Analyzing and translating with AI (GPT-4o)...")
    briefing = generate_analyst_brief(israel_news, ai_news, world_news, stocks_news)
    
    # 3. משלוח ליעד
    print("📤 Sending daily brief to Telegram...")
    send_to_telegram(briefing)
    
    print("🏁 Run complete.")
