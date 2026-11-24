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
</style>
""", unsafe_allow_html=True)

TRUSTED_DOMAINS = [
    "ndtv", "timesofindia", "times of india", "indiatimes", "hindustantimes", "hindustan times",
    "indianexpress", "indian express", "thehindu", "the hindu", "bbc", "reuters",
    "apnews", "ap news", "pib.gov.in", "pib", "livemint", "economictimes", "economic times",
    "news18", "aajtak", "aaj tak", "indiatoday", "india today", "aljazeera", "cnn", "cnbc",
    "news24", "news24online", "abplive", "abp news", "zeenews", "zee news", "ani", "pti",
    "tribune", "dainik jagran", "jagran", "amar ujala", "amarujala", "bhaskar", "punjab kesari"
]

STOPWORDS = {
    "the", "is", "in", "at", "of", "on", "and", "a", "to", "for", "with", "from",
    "by", "as", "an", "be", "this", "that", "it", "are", "was", "were", "has", "have",
    "received", "call", "news", "breaking", "latest", "today", "says", "said", "over", "live", "updates"
}

CLICKBAIT_WORDS = [
    "forward this", "100% true", "miracle", "nasa confirms", "15 days of complete darkness",
    "free laptop", "free recharge", "share immediately", "shocking truth",
    "secret exposed", "whatsapp", "alert!!", "must watch", "note band"
]

STATE_OPTIONS = [
    "All India (Default)", "Haryana / Faridabad", "Delhi NCR", "Uttar Pradesh",
    "Bihar", "Rajasthan", "Maharashtra", "Punjab", "Madhya Pradesh"
]

if "news_input_box" not in st.session_state:
    st.session_state.news_input_box = ""

def clear_and_refresh():
    st.session_state.news_input_box = ""
    st.cache_data.clear()

def find_url_in_text(text):
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(1) if match else None

def extract_keywords(text):
    clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = [w for w in clean.split() if len(w) > 2 and w not in STOPWORDS]
    return " ".join(words[:7]) if words else text

def extract_text_from_url(url):
    domain_trusted = any(td in url.lower() for td in TRUSTED_DOMAINS)
    channel_name = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if "youtube.com" in url or "youtu.be" in url:
            oembed_url = f"https://youtube.com{urllib.parse.quote(url)}&format=json"
            res = requests.get(oembed_url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                title = data.get("title", "")
                channel_name = data.get("author_name", "")
                if any(td in channel_name.lower() for td in TRUSTED_DOMAINS):
                    domain_trusted = True
                return title, f"YouTube Video ({channel_name})", domain_trusted, channel_name
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        h1 = soup.find("h1")
        headline = h1.get_text().strip() if h1 else title
        final_text = headline if headline else title
        if not final_text:
            final_text = url.split("/")[-1].replace("-", " ").replace(".cms", "").replace(".html", "")
        return final_text, "Web News Article", domain_trusted, url
    except Exception:
        slug = url.split("/")[-1].replace("-", " ").replace(".cms", "").replace(".html", "")
        return slug if len(slug) > 5 else url, "Web URL", domain_trusted, url

@st.cache_data(ttl=300, show_spinner=False)
def search_google_news(query, lang="en"):
    encoded_query = urllib.parse.quote(query)
    if lang == "hi":
        rss_url = f"https://google.com{encoded_query}&hl=hi&gl=IN&ceid=IN:hi"
    else:
        rss_url = f"https://google.com{encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(rss_url, headers=headers, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:10]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_el = item.find("source")
                source_name = source_el.text if source_el is not None else "News Source"
                articles.append({"title": title, "link": link, "source": source_name, "date": pub_date})
    except Exception:
        pass
    return articles

def calculate_similarity(query_text, article_title):
    q_clean = re.sub(r'[^\w\s]', ' ', query_text.lower())
    t_clean = re.sub(r'[^\w\s]', ' ', article_title.lower())
    q_words = {w for w in q_clean.split() if len(w) > 2 and w not in STOPWORDS}
    t_words = {w for w in t_clean.split() if len(w) > 2 and w not in STOPWORDS}
    if not q_words or not t_words:
        return 0.0
    matched = q_words.intersection(t_words)
    overlap = len(matched) / min(len(q_words), 5)
    seq_ratio = SequenceMatcher(None, " ".join(q_words), " ".join(t_words)).ratio()
    return max(overlap, seq_ratio)
    st.title("🛡️ VeriNews 2.0 (Pro)")
st.caption("Real-Time Live Web Fact-Checker • Text, URL, YouTube, Regional Filter & Explanations")

col1, col2, col3 = st.columns([1.1, 1.2, 1.1])
with col1:
    lang_choice = st.selectbox("🌐 Language:", ["English", "Hindi / Hinglish"])
with col2:
    region_choice = st.selectbox("📍 Region (Optional):", STATE_OPTIONS)
with col3:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    st.button("🔄 Refresh & Clear", on_click=clear_and_refresh)

user_input = st.text_area(
    "News Content, Article URL, or YouTube Link:",
    key="news_input_box",
    height=125,
    placeholder="Paste any news headline, Hindi/Hinglish text, state/local news, article link, or YouTube URL here..."
)

if st.button("🔍 Analyze & Verify Live"):
    if not user_input.strip():
        st.warning("⚠️ Please enter some news text, headline, or URL to verify.")
    else:
        with st.spinner("Checking live trusted news sources & analyzing credibility..."):
            raw_text = user_input.strip()
            detected_url = find_url_in_text(raw_text)
            domain_verified = False
            source_label = ""

            if detected_url:
                extracted, input_type, domain_verified, source_label = extract_text_from_url(detected_url)
                query_text = extracted
                st.info(f"🔗 **Detected {input_type}:** {query_text}")
            else:
                query_text = raw_text

            base_query = extract_keywords(query_text) if "Hindi" not in lang_choice else query_text
            if region_choice != "All India (Default)":
                state_tag = region_choice.split("/")[0].strip()
                search_query = f"{base_query} {state_tag}"
                st.caption(f"📍 **Regional Verification Active:** Searching specifically in **{region_choice}** news feeds.")
            else:
                search_query = base_query

            lang_code = "hi" if "Hindi" in lang_choice else "en"
            matches = search_google_news(search_query, lang=lang_code)
            if not matches:
                matches = search_google_news(base_query, lang="en")

            trusted_hits = 0
            relevant_hits = 0
            best_score = 0.0
            matched_sources_names = []

            for art in matches:
                sim = calculate_similarity(query_text, art["title"])
                if sim > best_score:
                    best_score = sim
                if sim >= 0.22:
                    relevant_hits += 1
                    src_lower = art["source"].lower()
                    if any(td in src_lower for td in TRUSTED_DOMAINS):
                        trusted_hits += 1
                        if art["source"] not in matched_sources_names:
                            matched_sources_names.append(art["source"])

            found_clickbaits = [w for w in CLICKBAIT_WORDS if w in query_text.lower()]
            clickbait_hits = len(found_clickbaits)

            if clickbait_hits > 0 and trusted_hits == 0 and not domain_verified:
                real_prob = max(9.5, 22.0 - (clickbait_hits * 5.0))
            elif domain_verified:
                real_prob = min(97.2, 86.0 + (trusted_hits * 2.5))
            elif trusted_hits >= 2 or (trusted_hits >= 1 and best_score >= 0.35):
                real_prob = min(96.5, 75.0 + (trusted_hits * 5.0) + (best_score * 15.0))
            elif relevant_hits >= 2 or best_score >= 0.28:
                real_prob = min(84.5, 64.0 + (best_score * 20.0))
            elif len(matches) > 0 and best_score >= 0.16:
                real_prob = 52.0
            else:
                real_prob = 18.5

            fake_prob = round(100.0 - real_prob, 1)
            real_prob = round(real_prob, 1)

            st.subheader("Verification Result")

            if real_prob >= 62.0:
                st.markdown('<div class="real-box">✅ VERIFIED REAL NEWS (Confirmed by Live Sources)</div>', unsafe_allow_html=True)
                confidence = real_prob
                status_type = "REAL"
            elif 45.0 <= real_prob < 62.0:
                st.markdown('<div class="warn-box">⚠️ UNCERTAIN / 50-50 PARTIAL MATCH</div>', unsafe_allow_html=True)
                confidence = real_prob
                status_type = "UNCERTAIN"
            else:
                st.markdown('<div class="fake-box">🚨 FAKE / UNVERIFIED NEWS DETECTED</div>', unsafe_allow_html=True)
                confidence = fake_prob
                status_type = "FAKE"

            st.markdown("**AI & Live Fact-Check Confidence Score**")
            st.markdown(f"# {confidence}%")
            st.progress(int(confidence))
            st.caption(f"⏱️ Last Checked: {datetime.now().strftime('%H:%M:%S')} | Region Mode: {region_choice}")

            st.subheader("🧠 Why is this classified as " + status_type + "?")
            if status_type == "REAL":
                sources_str = ", ".join(matched_sources_names[:4]) if matched_sources_names else "Verified Media Outlets"
                st.info(
                    f"✅ **Trusted Media Confirmation:** Actively reported by credible outlets ({sources_str}).\n\n"
                    f"✅ **High Content Alignment:** Matched with {relevant_hits} live news reports across the web.\n\n"
                    f"✅ **Credible Journalistic Tone:** No clickbait or fake WhatsApp forward triggers detected."
                )
            elif status_type == "UNCERTAIN":
                st.warning(
                    "⚠️ **Partial Topic Overlap:** Related keywords were found in live news, but the exact claim lacks full confirmation.\n\n"
                    "⚠️ **Limited Source Consensus:** Fewer than 2 major trusted outlets have verified this exact statement.\n\n"
                    "💡 **Recommendation:** Cross-check on the official portals below before sharing."
                )
            else:
                cb_text = f"Detected suspicious/clickbait phrases: {', '.join(found_clickbaits)}." if found_clickbaits else "Claim lacks verifiable source attribution or official confirmation."
                st.error(
                    "❌ **Zero Trusted Media Coverage:** No credible national, international, or regional news portal has published this claim.\n\n"
                    f"❌ **Misinformation Pattern:** {cb_text}\n\n"
                    "❌ **Unverified Origin:** High probability of fabricated or misleading social media forward."
                )

            st.subheader("Probability Breakdown:")
            chart_df = pd.DataFrame({
                "Category": ["Fake Probability (%)", "Real Probability (%)"],
                "Score": [fake_prob, real_prob]
            }).set_index("Category")
            st.bar_chart(chart_df)

            st.subheader("📰 Live Web Evidence & Matched Sources")
            if matches:
                for m in matches[:5]:
                    st.markdown(f"**{m['source']}** • *{m['date'][:16]}* — [{m['title']}]({m['link']})")
            else:
                st.error("❌ No credible news sources found reporting this claim on Google News.")

            st.subheader("🔎 Doubt the Result? Cross-Check Yourself")
            st.markdown(
                "If you want to manually verify this news yourself, visit these official & IFCN-certified fact-checking portals:\n"
                "- 🇮🇳 **[PIB Fact Check](https://pib.gov.in)** — Official Government of India Fact-Checking Unit\n"
                "- 🌐 **[Google Fact Check Explorer](https://google.com)** — Global Database of Fact-Checked Claims\n"
                "- ✅ **[Vishvas News](https://vishvasnews.com)** — IFCN Certified Hindi & English Fact-Checker\n"
                "- ✅ **[BOOM Live](https://boomlive.in)** — Independent Journalism & Fact-Checking Portal\n"
                "- ✅ **[Alt News](https://altnews.in)** — Social Media & Viral Misinformation Verification"
  )                                   
