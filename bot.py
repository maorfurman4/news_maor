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
    """שולח הכל ל-GPT-4o כדי שיערוך, יסנן ויתרגם לעברית ברמה גבוהה ועיצוב פרימיום"""
    date_today = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    אתה "סוכן אנליסט" אישי ויוקרתי. תפקידך לכתוב בריף בוקר למנהל בכיר.
    קבל את רשימת החדשות הגולמיות באנגלית. 
    המטרה שלך היא לייצר סיכום סופר-מעניין, קריא, מרווח ומושך לעין, שמותאם לקריאה מהירה בטלגרם.

    חוקי תוכן ועיצוב חובה (אל תסטה מהם!):
    1. בחר בדיוק את 3 הכתבות הכי חשובות מכל קטגוריה, ותרגם לעברית עסקית וזורמת.
    2. השתמש בהרבה רווחים (שורה ריקה) בין כתבה לכתבה כדי למנוע עומס בעין.
    3. שים אימוג'י ייחודי שקשור לנושא ליד כל כותרת של כתבה.
    4. השתמש בפורמט בולטים עשיר (ראה דוגמה מטה).
    5. את הקישורים שים כטקסט קליקבילי אלגנטי.

    לגבי "מעקב חברות": חפש דיווחים על החברות: {COMPANIES}. 
    אם יש חדשות, כתוב אותן בצורה מעניינת. אם אין, כתוב בדיוק: "💤 *אין דיווחים חריגים הבוקר לחברות במעקב.*"

    המידע הגולמי:
    ישראל: {israel}
    בינה מלאכותית: {ai}
    אקטואליה עולמית: {world}
    חברות ושוק ההון: {stocks}

    החזר את התשובה *בדיוק* בפורמט הבא:

    🌅 **בריף בוקר מנהלים - {date_today}** ☕

    🇮🇱 **ישראל**
    🔻 **[אימוג'י מתאים] [כותרת הכתבה המושכת]**
    💡 *השורה התחתונה:* [הסבר קצר, חד ומעניין ב-2 שורות]
    🔗 [לקריאת הכתבה המלאה](URL)
    
    [שורה ריקה]
    ... וכך הלאה לכל הקטגוריות.
    
    🤖 **בינה מלאכותית (AI)**
    ...
    🌍 **אקטואליה עולמית**
    ...
    📈 **מעקב חברות ותיק מניות**
    ...
    """

    try:
        if not OPENAI_API_KEY:
            print("❌ ERROR: OPENAI_API_KEY is missing!")
            return "שגיאה: חסר מפתח OpenAI."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4 # קצת יותר יצירתיות בשביל הניסוח והאימוג'ים
        }
        
        print("🧠 Sending request to OpenAI for stylized brief...")
        response = requests.post(url, json=payload, headers=headers)
        
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
