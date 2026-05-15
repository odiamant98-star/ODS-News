import feedparser
import google.generativeai as genai
import streamlit as st
import urllib.parse
import time
from datetime import datetime

# --- הגדרות עיצוב עדינות לעיניים ועיצוב טאבים ---
st.set_page_config(page_title="ODS", page_icon="📊", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600&display=swap');
    
    .stApp, .stMarkdown, p, li, span, div, input { 
        direction: rtl !important; 
        text-align: right !important; 
        font-family: 'Rubik', sans-serif !important; 
        color: #2D3748 !important; 
    }
    
    .stApp { background-color: #E8ECEF !important; }
    
    [data-testid="stSidebar"] { 
        background-color: #DFE4E8 !important; 
        border-left: 1px solid #CBD5E1;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* עיצוב הטאבים (לשוניות) */
    button[data-baseweb="tab"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        background-color: #DFE4E8 !important;
        border-radius: 8px 8px 0 0 !important;
        margin-left: 8px !important;
        border: 1px solid #CBD5E1 !important;
        border-bottom: none !important;
        padding: 10px 20px !important;
    }
    button[aria-selected="true"] {
        background-color: #F1F4F6 !important;
        color: #2B6CB0 !important;
        border-bottom: 3px solid #2B6CB0 !important;
        z-index: 1;
    }
    
    .stButton>button { 
        width: 100%; 
        font-weight: 600; 
        border-radius: 12px !important;
        background: #2B6CB0 !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(43, 108, 176, 0.2) !important;
        transition: 0.3s;
    }
    .stButton>button:hover { background: #2c5282 !important; }
    
    h3 {
        background-color: #F1F4F6 !important; 
        padding: 18px 20px 10px 20px;
        border-radius: 16px 16px 0 0;
        margin-top: 25px !important;
        margin-bottom: 0px !important;
        border: 1px solid #CBD5E1;
        border-bottom: none;
    }
    
    h3 + ul {
        background-color: #F1F4F6 !important;
        padding: 10px 40px 20px 20px !important;
        border-radius: 0 0 16px 16px;
        border: 1px solid #CBD5E1;
        border-top: none;
        margin-top: 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        list-style-type: none !important; /* הסרת הנקודות מהרשימה כדי שהעיצוב יהיה נקי */
    }
    
    /* עיצוב הלינק לכתבה */
    a {
        color: #2B6CB0 !important;
        font-weight: 600;
        text-decoration: none;
        background-color: #E2E8F0;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 8px;
        transition: 0.2s;
    }
    a:hover { background-color: #CBD5E1; text-decoration: none !important; }
    
    hr { display: none; }
    
    [data-testid="stChatMessage"] {
        background-color: #F1F4F6 !important;
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        border: 1px solid #CBD5E1;
        margin-bottom: 12px;
    }
    
    .stTextInput>div>div>input {
        background-color: #F1F4F6 !important;
        border-radius: 12px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 10px !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- חיבור מאובטח לג'מיני ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
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
            אתה אנליסט השקעות בכיר. עליך להכין בריף המחולק לשוק המקומי ולשווקים גלובליים.
            
            חוקים נוקשים:
            1. הכתבות שמועברות אליך מטה **כבר ממוינות מהחדשה ביותר לישנה ביותר**. שמור על סדר כרונולוגי זה.
            2. בחר עד 5 כתבות מקומיות ועד 5 כתבות גלובליות.
            3. תרגם את הכתבות הגלובליות לעברית פיננסית.
            4. **חובה:** הפרד בין החלק המקומי לגלובלי באמצעות השורה המדויקת הבאה בלבד (בלי תוספות, כותרות או סימנים אחרים לידה):
            ---SPLIT---
            
            פורמט נדרש לכל כתבה:
            ### כותרת הכתבה *(מקור: מזהה המקור | פורסם ב: תאריך)*
            * **שורת מחץ:** תקציר של 2-3 משפטים.
            * **משמעות לשוק:** ההשפעה האפשרית על התיקים.
            * 🔗 [למעבר לכתבה המלאה לחץ כאן]({"{קישור}"})
            <br>
            
            מבנה התשובה הנדרש בדיוק:
            [הכתבות המקומיות כאן]
            ---SPLIT---
            [הכתבות הגלובליות כאן]
            
            רשימת חדשות מקומיות גולמית:
            {local_news_text}

            רשימת חדשות גלובליות גולמית:
            {global_news_text}
            """
            
            try:
                response = model.generate_content(prompt)
                st.session_state.brief_content = response.text
                st.session_state.chat_history = [] 
            except Exception as e:
                st.error(f"שגיאה בתקשורת עם ג'מיני: {e}")

# --- תצוגת הבריף (עם הטאבים) והצ'אט ---
if st.session_state.brief_content:
    st.success("הבריף מוכן!")
    
    # פיצול התוכן לטאבים
    content = st.session_state.brief_content
    if "---SPLIT---" in content:
        parts = content.split("---SPLIT---")
        if len(parts) == 2:
            tab1, tab2 = st.tabs(["🇮🇱 שוק מקומי", "🌍 שווקים גלובליים"])
            with tab1:
                st.markdown(parts[0].strip(), unsafe_allow_html=True)
            with tab2:
                st.markdown(parts[1].strip(), unsafe_allow_html=True)
        else:
            # מקרה חירום בו ג'מיני התבלבל במבנה
            st.markdown(content, unsafe_allow_html=True)
    else:
        st.markdown(content, unsafe_allow_html=True)
    
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