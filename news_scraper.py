import feedparser
import google.generativeai as genai
import streamlit as st
import urllib.parse
import time
from datetime import datetime

# --- הגדרות עיצוב מתקדמות: פונט מודרני, חלוניות וצבעים בהירים ---
st.set_page_config(page_title="ODS", page_icon="📊", layout="wide")
st.markdown("""
    <style>
    /* ייבוא פונט מודרני (Rubik) מגוגל פונטס */
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600&display=swap');
    
    .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, li, span, div, input { 
        direction: rtl !important; 
        text-align: right !important; 
        font-family: 'Rubik', sans-serif !important; 
    }
    
    /* צבע רקע כללי בהיר ורך */
    .stApp {
        background-color: #f3f6f9;
    }
    
    /* סרגל צד נקי ולבן */
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-left: 1px solid #e2e8f0;
    }
    
    /* עיצוב כפתור ההפעלה למודרני ומעוגל */
    .stButton>button { 
        width: 100%; 
        font-weight: 600; 
        border-radius: 20px !important;
        background: linear-gradient(135deg, #007aff, #005bb5) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 122, 255, 0.2) !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 122, 255, 0.35) !important;
    }
    
    /* --- קסם החלוניות (Cards) --- */
    /* לוקח את הכותרת של הכתבה והופך אותה לראש החלונית */
    h3 {
        background-color: #ffffff;
        padding: 18px 20px 10px 20px;
        border-radius: 16px 16px 0 0;
        margin-top: 25px !important;
        margin-bottom: 0px !important;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        color: #1e293b !important;
        font-size: 1.15rem !important;
    }
    h3 a { text-decoration: none !important; color: #007aff !important; }
    
    /* לוקח את גוף הכתבה ועוטף אותו בחלק התחתון של החלונית עם צללית */
    h3 + ul {
        background-color: #ffffff;
        padding: 10px 40px 20px 20px !important;
        border-radius: 0 0 16px 16px;
        border: 1px solid #e2e8f0;
        border-top: none;
        margin-top: 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* מסתיר את קווי ההפרדה הרגילים כי עכשיו יש לנו חלוניות */
    hr { display: none; }
    
    /* עיצוב בועות הצ'אט כחלוניות שיחה */
    [data-testid="stChatMessage"] {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }
    
    /* עיצוב שורת החיפוש */
    .stTextInput>div>div>input {
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- חיבור מאובטח לג'מיני (תומך גם בענן וגם במחשב) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    # מיועד להרצה המקומית על המחשב שלך
    API_KEY = "AIzaSyBCsaiu6uyALk1bph44Lnw3FUfiWu1JZJs" 

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
st.title("📊 MY NEWS")
st.write("מערכת AI שמחפשת באופן אקטיבי את הנושאים שלך, ממיינת לפי תאריך ומנתחת.")

if st.button("🔄 חפש, מיין ונתח עכשיו", type="primary"):
    with st.spinner("מחפש בארכיון החדשות בארץ ובעולם, ממיין תאריכים ומכין בריף..."):
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