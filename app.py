import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import xml.etree.ElementTree as ET
import re
from difflib import SequenceMatcher
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="VeriNews 2.0 - Live Fact Checker", page_icon="🛡️", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea { background-color: #262730 !important; color: #ffffff !important; border-radius: 8px; }
    div.stButton > button:first-child {
        background-color: #c8333a; color: white; width: 100%; border-radius: 8px;
        height: 48px; font-weight: bold; border: none; font-size: 16px;
    }
    div.stButton > button:first-child:hover { background-color: #a8282e; }
    .real-box { background-color: #133b27; border-left: 5px solid #28a745; padding: 15px; border-radius: 8px; color: #d4edda; font-weight: bold; font-size: 18px; }
    .fake-box { background-color: #3e191b; border-left: 5px solid #dc3545; padding: 15px; border-radius: 8px; color: #f8d7da; font-weight: bold; font-size: 18px; }
    .warn-box { background-color: #3d3214; border-left: 5px solid #ffc107; padding: 15px; border-radius: 8px; color: #fff3cd; font-weight: bold; font-size: 18px; }
    .source-card { background-color: #1c1f26; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #2d3139; }
</style>
""", unsafe_allow_html=True)

TRUSTED_DOMAINS = [
    "ndtv", "timesofindia", "indiatimes", "hindustantimes", "indianexpress",
    "thehindu", "bbc", "reuters", "apnews", "pib.gov.in", "livemint",
    "economictimes", "news18", "aajtak", "indiatoday", "aljazeera", "cnn", "cnbc"
]

CLICKBAIT_WORDS = [
    "breaking news", "forward this", "100% true", "miracle", "nasa confirms",
    "free laptop", "free recharge", "share immediately", "shocking truth",
    "secret exposed", "whatsapp", "alert!!", "must watch"
]

def extract_text_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if "youtube.com" in url or "youtu.be" in url:
            oembed_url = f"https://youtube.com{urllib.parse.quote(url)}&format=json"
            res = requests.get(oembed_url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                return f"{data.get('title', '')} - {data.get('author_name', '')}", "YouTube Video"
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        h1 = soup.find("h1")
        headline = h1.get_text().strip() if h1 else title
        return headline if headline else title, "Web Article"
    except Exception:
        return url, "URL"

@st.cache_data(ttl=300, show_spinner=False)
def search_google_news(query, lang="en"):
    encoded_query = urllib.parse.quote(query)
    if lang == "hi":
        rss_url = f"https://google.com{encoded_query}&hl=hi&gl=IN&ceid=IN:hi"
    else:
        rss_url = f"https://google.com{encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    articles = []
    try:
        res = requests.get(rss_url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:8]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_el = item.find("source")
                source_name = source_el.text if source_el is not None else "News Source"
                articles.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "date": pub_date
                })
    except Exception:
        pass
    return articles

def calculate_similarity(a, b):
    a_clean = re.sub(r'[^\w\s]', '', a.lower())
    b_clean = re.sub(r'[^\w\s]', '', b.lower())
    words_a = set(a_clean.split())
    words_b = set(b_clean.split())
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a.intersection(words_b)) / max(len(words_a), 1)
    seq_ratio = SequenceMatcher(None, a_clean, b_clean).ratio()
    return max(overlap, seq_ratio)

st.title("🛡️ VeriNews 2.0 (Pro)")
st.caption("Real-Time Live Web Fact-Checker • Text, URL, YouTube & Hindi/English Support")

col1, col2 = st.columns([2, 1])
with col1:
    lang_choice = st.selectbox("Search Language:", ["English", "Hindi / Hinglish"], label_visibility="collapsed")
with col2:
    if st.button("🔄 Refresh Source"):
        st.cache_data.clear()
        st.toast("Live News Cache Cleared & Refreshed!", icon="✅")

user_input = st.text_area(
    "News Content, Article URL, or YouTube Link:",
    height=130,
    placeholder="Paste any random news headline, Hindi/Hinglish message, news website link, or YouTube URL here..."
)

if st.button("🔍 Analyze & Verify Live"):
    if not user_input.strip():
        st.warning("⚠️ Please enter some news text, headline, or URL to verify.")
    else:
        with st.spinner("Checking live trusted news sources across the web..."):
            raw_text = user_input.strip()
            input_type = "Text / Headline"
            if raw_text.startswith("http://") or raw_text.startswith("https://"):
                extracted, input_type = extract_text_from_url(raw_text)
                query_text = extracted
                st.info(f"🔗 **Detected {input_type}:** {query_text}")
            else:
                query_text = raw_text

            lang_code = "hi" if "Hindi" in lang_choice else "en"
            matches = search_google_news(query_text, lang=lang_code)
            if not matches and lang_code == "hi":
                matches = search_google_news(query_text, lang="en")

            trusted_hits = 0
            best_score = 0.0
            for art in matches:
                sim = calculate_similarity(query_text, art["title"])
                if sim > best_score:
                    best_score = sim
                src_lower = art["source"].lower()
                if any(td in src_lower for td in TRUSTED_DOMAINS) and sim >= 0.30:
                    trusted_hits += 1

            clickbait_hits = sum(1 for w in CLICKBAIT_WORDS if w in query_text.lower())

            real_prob = 20.0
            if trusted_hits >= 2 and best_score >= 0.35:
                real_prob = min(96.5, 70.0 + (trusted_hits * 6.0) + (best_score * 15.0))
            elif trusted_hits == 1 or best_score >= 0.35:
                real_prob = min(82.0, 55.0 + (best_score * 25.0))
            elif len(matches) > 0 and best_score >= 0.22:
                real_prob = 50.5
            else:
                real_prob = max(8.5, 28.0 - (clickbait_hits * 7.0))

            if clickbait_hits > 0 and trusted_hits == 0:
                real_prob = min(real_prob, 24.0)

            fake_prob = round(100.0 - real_prob, 1)
            real_prob = round(real_prob, 1)

            st.subheader("Verification Result")

            if real_prob >= 62.0:
                st.markdown('<div class="real-box">✅ VERIFIED REAL NEWS (Confirmed by Live Sources)</div>', unsafe_allow_html=True)
                confidence = real_prob
                explanation = f"Matched with {len(matches)} live news reports ({trusted_hits} from major trusted outlets)."
            elif 45.0 <= real_prob < 62.0:
                st.markdown('<div class="warn-box">⚠️ UNCERTAIN / 50-50 PARTIAL MATCH</div>', unsafe_allow_html=True)
                confidence = real_prob
                explanation = "Partial keyword overlap found on the web, but exact claim lacks strong confirmation."
            else:
                st.markdown('<div class="fake-box">🚨 FAKE / UNVERIFIED NEWS DETECTED</div>', unsafe_allow_html=True)
                confidence = fake_prob
                explanation = "No matching reports found in trusted news outlets. High likelihood of misinformation or fabrication."

            st.markdown("**AI & Live Fact-Check Confidence Score**")
            st.markdown(f"# {confidence}%")
            st.progress(int(confidence))
            st.caption(f"💡 **Analysis Reason:** {explanation} | Last Checked: {datetime.now().strftime('%H:%M:%S')}")

            st.subheader("Probability Breakdown:")
            chart_df = pd.DataFrame({
                "Category": ["Fake Probability (%)", "Real Probability (%)"],
                "Score": [fake_prob, real_prob]
            }).set_index("Category")
            st.bar_chart(chart_df)

            st.subheader("📰 Live Web Evidence & Matched Sources")
            if matches:
                for m in matches[:5]:
                    st.markdown(f"""
                    <div class="source-card">
                        <b>{m['source']}</b> • <small>{m['date'][:16]}</small><br>
                        <a href="{m['link']}" target="_blank" style="color:#58a6ff; text-decoration:none;">{m['title']} ↗</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ No credible news sources found reporting this claim on Google News.")

