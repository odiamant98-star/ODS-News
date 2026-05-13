import feedparser
import google.generativeai as genai
import streamlit as st
import urllib.parse
import time
from datetime import datetime

# --- הגדרות עיצוב ויישור מוחלט לימין (RTL) ---
# שינוי שם הלשונית בדפדפן ל-ODS
st.set_page_config(page_title="ODS", page_icon="📊", layout="wide")
st.markdown("""
    <style>
    .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, li, span, div { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    [data-testid="stSidebar"] { direction: rtl !important; text-align: right !important; }
    .stButton>button { width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- חיבור לג'מיני ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

if "brief_content" not in st.session_state:
    st.session_state.brief_content = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- תפריט צד ---
with st.sidebar:
    st.header("⚙️ במה נתמקד היום?")
    user_topics = st.text_input(
        "הקלד נושאים לחיפוש (הפרד בפסיק):",
        value="Oracle, אינפלציה, שוק ההון"
    )

# --- המסך הראשי ---
# שינוי הכותרת הראשית ל-MY NEWS
st.title("📊 MY NEWS")
st.write("מערכת AI שמחפשת באופן אקטיבי את הנושאים שלך, ממיינת לפי תאריך ומנתחת.")

if st.button("🔄 חפש, מיין ונתח עכשיו", type="primary"):
    with st.spinner("מחפש בארכיון החדשות בארץ ובעולם, ממיין תאריכים ומכין בריף..."):
        
        # פיצול הנושאים שהמשתמש הקליד לרשימה
        topics_list = [t.strip() for t in user_topics.split(',') if t.strip()]
        
        def fetch_historical_news(topics, is_local=True):
            articles = []
            for topic in topics:
                encoded_topic = urllib.parse.quote(topic)
                
                if is_local:
                    url = f"https://news.google.com/rss/search?q={encoded_topic}+when:30d&hl=he&gl=IL&ceid=IL:he"
                else:
                    url = f"https://news.google.com/rss/search?q={encoded_topic}+when:30d&hl=en-US&gl=US&ceid=US:en"
                
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:10]:
                    timestamp = time.mktime(entry.published_parsed) if entry.get('published_parsed') else 0
                    published_date = entry.get('published', 'תאריך לא ידוע')
                    source_name = entry.source.title if 'source' in entry else "Google News"
                    
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": source_name,
                        "date": published_date,
                        "timestamp": timestamp,
                        "topic_searched": topic
                    })
            
            # מיון מהחדש לישן
            articles.sort(key=lambda x: x['timestamp'], reverse=True)
            return articles

        local_articles = fetch_historical_news(topics_list, is_local=True)
        global_articles = fetch_historical_news(topics_list, is_local=False)
        
        def format_for_gemini(articles_list):
            text = ""
            for i, art in enumerate(articles_list[:15], 1):
                text += f"- כותרת: {art['title']}\n  מקור: {art['source']} | תאריך: {art['date']}\n  קישור: {art['link']}\n\n"
            return text

        local_news_text = format_for_gemini(local_articles)
        global_news_text = format_for_gemini(global_articles)
        
        if not local_news_text and not global_news_text:
            st.error("לא נמצאו כתבות כלל עבור נושאים אלו בחודש האחרון.")
        else:
            prompt = f"""
            אתה אנליסט השקעות בכיר. עליך להכין בריף המחולק לשוק המקומי ולשווקים גלובליים, בהתבסס על הכתבות שנאספו בחודש האחרון.
            
            חוקים נוקשים:
            1. הכתבות שמועברות אליך מטה **כבר ממוינות מהחדשה ביותר לישנה ביותר**. חובה עליך לשמור על סדר כרונולוגי זה בדיוק כפי שהוא מופיע.
            2. בחר עד 5 כתבות מקומיות ועד 5 כתבות גלובליות. אם אין מספיק, הצג רק את מה שיש.
            3. חובה לציין ליד כל כותרת את המקור ואת התאריך שהתקבל.
            4. תרגם את הכתבות הגלובליות לעברית פיננסית.
            
            פורמט נדרש לכל כתבה:
            ### [כותרת הכתבה]({"{קישור}"}) *(מקור: מזהה המקור | פורסם ב: תאריך)*
            * **שורת מחץ:** תקציר של 2-3 משפטים.
            * **משמעות לשוק:** ההשפעה האפשרית על התיקים.
            ---
            
            רשימת חדשות מקומיות גולמית (מסודר מהחדש לישן):
            {local_news_text}

            רשימת חדשות גלובליות גולמית (מסודר מהחדש לישן):
            {global_news_text}
            """
            
            try:
                response = model.generate_content(prompt)
                st.session_state.brief_content = response.text
                st.session_state.chat_history = [] 
            except Exception as e:
                st.error(f"שגיאה בתקשורת עם ג'מיני: {e}")

# --- תצוגת הבריף והצ'אט ---
if st.session_state.brief_content:
    st.success("הבריף מוכן!")
    st.markdown(st.session_state.brief_content)
    
    st.divider()
    st.subheader("💬 התייעץ עם האנליסט שלך")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_question := st.chat_input("שאל על הכתבות, או בקש הרחבה..."):
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            chat_context = f"בריף יומי:\n{st.session_state.brief_content}\n\nשאלה:\n{user_question}"
            response = model.generate_content(chat_context)
            st.markdown(response.text)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response.text})