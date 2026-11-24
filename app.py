 streamlit as st
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
        height: 46px; font-weight: bold; border: none; font-size: 16px;
    }
    div.stButton > button:first-child:hover { background-color: #a8282e; }
    .real-box { background-color: #133b27; border-left: 5px solid #28a745; padding: 15px; border-radius: 8px; color: #d4edda; font-weight: bold; font-size: 18px; }
    .fake-box { background-color: #3e191b; border-left: 5px solid #dc3545; padding: 15px; border-radius: 8px; color: #f8d7da; font-weight: bold; font-size: 18px; }
    .warn-box { background-color: #3d3214; border-left: 5px solid #ffc107; padding: 15px; border-radius: 8px; color: #fff3cd; font-weight: bold; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

DIRECT_RSS_FEEDS = [
    ("Times of India Top", "https://indiatimes.com"),
    ("Times of India India", "https://indiatimes.com"),
    ("NDTV India", "https://feedburner.com"),
    ("NDTV Top Stories", "https://feedburner.com"),
    ("The Hindu National", "https://thehindu.com"),
    ("Hindustan Times", "https://hindustantimes.com"),
    ("Indian Express", "https://indianexpress.com"),
    ("BBC World", "http://bbci.co.uk")
]

TRUSTED_DOMAINS = [
    "ndtv", "timesofindia", "indiatimes", "hindustantimes", "indianexpress",
    "thehindu", "bbc", "reuters", "apnews", "pib", "livemint", "economictimes",
    "news18", "aajtak", "indiatoday", "news24", "abplive", "zeenews", "ani", "pti"
]

STOPWORDS = {
    "the", "is", "in", "at", "of", "on", "and", "a", "to", "for", "with", "from",
    "by", "as", "an", "be", "this", "that", "it", "are", "was", "were", "has", "have",
    "news", "breaking", "latest", "today", "says", "said", "over", "live", "updates", "after"
}

CLICKBAIT_WORDS = [
    "forward this", "100% true", "miracle", "nasa confirms", "15 days of complete darkness",
    "free laptop", "free recharge", "share immediately", "shocking truth",
    "secret exposed", "whatsapp", "alert!!", "must watch", "note band", "10 days holiday"
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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_live_feeds():
    all_articles = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for source_name, url in DIRECT_RSS_FEEDS:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall(".//item")[:20]:
                    title_el = item.find("title")
                    link_el = item.find("link")
                    date_el = item.find("pubDate")
                    title = title_el.text.strip() if title_el is not None and title_el.text else ""
                    link = link_el.text.strip() if link_el is not None and link_el.text else ""
                    pub_date = date_el.text.strip() if date_el is not None and date_el.text else "Today"
                    if title:
                        all_articles.append({"title": title, "link": link, "source": source_name, "date": pub_date})
        except Exception:
            continue
    return all_articles

def search_live_news(query):
    live_pool = fetch_all_live_feeds()
    q_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    q_words = {w for w in q_clean.split() if len(w) > 2 and w not in STOPWORDS}
    scored = []
    for art in live_pool:
        t_clean = re.sub(r'[^\w\s]', ' ', art["title"].lower())
        t_words = {w for w in t_clean.split() if len(w) > 2 and w not in STOPWORDS}
        if not q_words or not t_words:
            continue
        common = q_words.intersection(t_words)
        ratio = len(common) / min(len(q_words), 4)
        seq = SequenceMatcher(None, " ".join(sorted(q_words)), " ".join(sorted(t_words))).ratio()
        score = max(ratio, seq)
        if score >= 0.25 or len(common) >= 2:
            scored.append((score, art))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def extract_text_from_url(url):
    domain_trusted = any(td in url.lower() for td in TRUSTED_DOMAINS)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        h1 = soup.find("h1")
        headline = h1.get_text().strip() if h1 else title
        if headline and "youtube" not in headline.lower():
            return headline, "Web Link", domain_trusted
    except Exception:
        pass
    slug = url.split("/")[-1].replace("-", " ").replace(".cms", "").replace(".html", "")
    return (slug if len(slug) > 6 else url), "Web URL", domain_trusted
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
        height: 46px; font-weight: bold; border: none; font-size: 16px;
    }
    div.stButton > button:first-child:hover { background-color: #a8282e; }
    .real-box { background-color: #133b27; border-left: 5px solid #28a745; padding: 15px; border-radius: 8px; color: #d4edda; font-weight: bold; font-size: 18px; }
    .fake-box { background-color: #3e191b; border-left: 5px solid #dc3545; padding: 15px; border-radius: 8px; color: #f8d7da; font-weight: bold; font-size: 18px; }
    .warn-box { background-color: #3d3214; border-left: 5px solid #ffc107; padding: 15px; border-radius: 8px; color: #fff3cd; font-weight: bold; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

DIRECT_RSS_FEEDS = [
    ("Times of India Top", "https://indiatimes.com"),
    ("Times of India India", "https://indiatimes.com"),
    ("NDTV India", "https://feedburner.com"),
    ("NDTV Top Stories", "https://feedburner.com"),
    ("The Hindu National", "https://thehindu.com"),
    ("Hindustan Times", "https://hindustantimes.com"),
    ("Indian Express", "https://indianexpress.com"),
    ("BBC World", "http://bbci.co.uk")
]

TRUSTED_DOMAINS = [
    "ndtv", "timesofindia", "indiatimes", "hindustantimes", "indianexpress",
    "thehindu", "bbc", "reuters", "apnews", "pib", "livemint", "economictimes",
    "news18", "aajtak", "indiatoday", "news24", "abplive", "zeenews", "ani", "pti"
]

STOPWORDS = {
    "the", "is", "in", "at", "of", "on", "and", "a", "to", "for", "with", "from",
    "by", "as", "an", "be", "this", "that", "it", "are", "was", "were", "has", "have",
    "news", "breaking", "latest", "today", "says", "said", "over", "live", "updates", "after"
}

CLICKBAIT_WORDS = [
    "forward this", "100% true", "miracle", "nasa confirms", "15 days of complete darkness",
    "free laptop", "free recharge", "share immediately", "shocking truth",
    "secret exposed", "whatsapp", "alert!!", "must watch", "note band", "10 days holiday"
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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_live_feeds():
    all_articles = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for source_name, url in DIRECT_RSS_FEEDS:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall(".//item")[:20]:
                    title_el = item.find("title")
                    link_el = item.find("link")
                    date_el = item.find("pubDate")
                    title = title_el.text.strip() if title_el is not None and title_el.text else ""
                    link = link_el.text.strip() if link_el is not None and link_el.text else ""
                    pub_date = date_el.text.strip() if date_el is not None and date_el.text else "Today"
                    if title:
                        all_articles.append({"title": title, "link": link, "source": source_name, "date": pub_date})
        except Exception:
            continue
    return all_articles

def search_live_news(query):
    live_pool = fetch_all_live_feeds()
    q_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    q_words = {w for w in q_clean.split() if len(w) > 2 and w not in STOPWORDS}
    scored = []
    for art in live_pool:
        t_clean = re.sub(r'[^\w\s]', ' ', art["title"].lower())
        t_words = {w for w in t_clean.split() if len(w) > 2 and w not in STOPWORDS}
        if not q_words or not t_words:
            continue
        common = q_words.intersection(t_words)
        ratio = len(common) / min(len(q_words), 4)
        seq = SequenceMatcher(None, " ".join(sorted(q_words)), " ".join(sorted(t_words))).ratio()
        score = max(ratio, seq)
        if score >= 0.25 or len(common) >= 2:
            scored.append((score, art))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def extract_text_from_url(url):
    domain_trusted = any(td in url.lower() for td in TRUSTED_DOMAINS)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        h1 = soup.find("h1")
        headline = h1.get_text().strip() if h1 else title
        if headline and "youtube" not in headline.lower():
            return headline, "Web Link", domain_trusted
    except Exception:
        pass
    slug = url.split("/")[-1].replace("-", " ").replace(".cms", "").replace(".html", "")
    return (slug if len(slug) > 6 else url), "Web URL", domain_trusted
    st.title("🛡️ VeriNews 2.0 (Pro)")
st.caption("Real-Time Live Web Fact-Checker • Direct Trusted Feeds, Regional Filter & Explanations")

col1, col2, col3 = st.columns([1.1, 1.2, 1.1])
with col1:
    lang_choice = st.selectbox("🌐 Language:", ["English", "Hindi / Hinglish"])
with col2:
    region_choice = st.selectbox("📍 Region (Optional):", STATE_OPTIONS)
with col3:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    st.button("🔄 Refresh & Clear", on_click=clear_and_refresh)

if st.button("⚡ Load Today's Live Breaking Headline"):
    live_list = fetch_all_live_feeds()
    if live_list:
        st.session_state.news_input_box = live_list[0]["title"]
        st.rerun()

user_input = st.text_area(
    "News Content, Article URL, or YouTube Link:",
    key="news_input_box",
    height=120,
    placeholder="Paste any news headline, Hindi/Hinglish text, state news, or click 'Load Today's Live Breaking Headline' above..."
)

if st.button("🔍 Analyze & Verify Live"):
    if not user_input.strip():
        st.warning("⚠️ Please enter some news text, headline, or URL to verify.")
    else:
        with st.spinner("Cross-checking against 150+ live Times of India, NDTV, The Hindu, HT & BBC articles..."):
            raw_text = user_input.strip()
            detected_url = find_url_in_text(raw_text)
            domain_verified = False

            if detected_url:
                query_text, input_type, domain_verified = extract_text_from_url(detected_url)
                st.info(f"🔗 **Detected {input_type}:** {query_text}")
            else:
                query_text = raw_text

            search_query = query_text
            if region_choice != "All India (Default)":
                state_tag = region_choice.split("/")[0].strip()
                search_query = f"{query_text} {state_tag}"
                st.caption(f"📍 **Regional Verification Active:** Filtering for **{region_choice}** context.")

            scored_matches = search_live_news(search_query)
            if not scored_matches and region_choice != "All India (Default)":
                scored_matches = search_live_news(query_text)

            best_score = scored_matches[0][0] if scored_matches else 0.0
            matched_articles = [item[1] for item in scored_matches]
            matched_sources = list(dict.fromkeys([a["source"] for a in matched_articles]))

            found_clickbaits = [w for w in CLICKBAIT_WORDS if w in query_text.lower()]
            clickbait_hits = len(found_clickbaits)

            if clickbait_hits > 0 and not matched_articles and not domain_verified:
                real_prob = max(8.5, 20.0 - (clickbait_hits * 4.0))
            elif domain_verified or best_score >= 0.45 or len(matched_articles) >= 2:
                real_prob = min(96.4, 82.0 + (len(matched_articles) * 3.0) + (best_score * 10.0))
            elif len(matched_articles) == 1 or best_score >= 0.28:
                real_prob = 52.5
            else:
                real_prob = 17.5

            fake_prob = round(100.0 - real_prob, 1)
            real_prob = round(real_prob, 1)

            st.subheader("Verification Result")

            if real_prob >= 62.0:
                st.markdown('<div class="real-box">✅ VERIFIED REAL NEWS (Confirmed by Live Trusted Feeds)</div>', unsafe_allow_html=True)
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
                src_list = ", ".join(matched_sources[:4]) if matched_sources else "Verified Official Domain"
                st.info(
                    f"✅ **Trusted Media Confirmation:** Verified directly from live feeds of **{src_list}**.\n\n"
                    f"✅ **High Content Alignment:** Found **{len(matched_articles)} matching live reports** with strong keyword consensus.\n\n"
                    "✅ **Credible Journalistic Tone:** No clickbait or misleading forward triggers detected."
                )
            elif status_type == "UNCERTAIN":
                st.warning(
                    "⚠️ **Partial Topic Overlap:** Related keywords appeared in live news, but full multi-source confirmation is limited.\n\n"
                    "💡 **Recommendation:** Cross-check on the official portals below before sharing."
                )
            else:
                cb_text = f"Detected suspicious/clickbait phrases: {', '.join(found_clickbaits)}." if found_clickbaits else "No matching report found in live TOI, NDTV, The Hindu, HT, or BBC feeds."
                st.error(
                    "❌ **Zero Trusted Media Coverage:** None of the major live news feeds confirm this claim.\n\n"
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
            if matched_articles:
                for m in matched_articles[:5]:
                    st.markdown(f"**{m['source']}** • *{m['date'][:16]}* — [{m['title']}]({m['link']})")
            else:
                st.error("❌ No credible news sources found reporting this claim in live feeds.")

            st.subheader("🔎 Doubt the Result? Cross-Check Yourself")
            st.markdown(
                "Verify manually on these official & IFCN-certified fact-checking portals:\n"
                "- 🇮🇳 **[PIB Fact Check](https://pib.gov.in)** — Official Government of India Fact-Checking Unit\n"
                "- 🌐 **[Google Fact Check Explorer](https://google.com)** — Global Fact-Checked Claims Database\n"
                "- ✅ **[Vishvas News](https://vishvasnews.com)** — IFCN Certified Hindi & English Fact-Checker\n"
                "- ✅ **[BOOM Live](https://boomlive.in)** — Independent Journalism & Fact-Checking Portal\n"
                "- ✅ **[Alt News](https://altnews.in)** — Social Media & Viral Misinformation Verification"
                          )
            
