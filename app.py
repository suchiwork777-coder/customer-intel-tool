"""
Customer Intelligence Tool
---------------------------
Helps a Customer Success Manager (CSM) answer two questions daily:
1. What is happening inside my customer's organisation?
2. What useful insight can I share with the customer today?

No paid APIs. Uses:
- Google News RSS (free, public) for real-time company signals
- Groq API (free tier) as the LLM to synthesize signals into a brief
"""

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Customer Intelligence Tool", page_icon="🧠", layout="wide")

# ---------------------------
# CONFIG
# ---------------------------
GROQ_MODEL = "openai/gpt-oss-20b"  # fast + free on Groq; update if Groq retires this model
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_api_key():
    """Get Groq API key from Streamlit secrets, or let user paste one for a demo run."""
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    return st.session_state.get("manual_api_key", "")


# ---------------------------
# DATA COLLECTION (free sources)
# ---------------------------
def fetch_google_news(query, max_items=8):
    """Pull recent news headlines for a query via Google News RSS (no API key needed)."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "Unknown"
            items.append({"title": title, "link": link, "pub_date": pub_date, "source": source})
        return items
    except Exception as e:
        st.warning(f"Could not fetch news for '{query}': {e}")
        return []


def collect_signals(company_name):
    """Collect signals across a few angles that matter to a CSM."""
    signals = {}
    signals["General News"] = fetch_google_news(f'"{company_name}"', max_items=8)
    signals["Leadership & Hiring"] = fetch_google_news(
        f'"{company_name}" (executive OR hire OR appoints OR layoffs OR restructuring)', max_items=5
    )
    signals["Funding & Financials"] = fetch_google_news(
        f'"{company_name}" (funding OR earnings OR acquisition OR revenue)', max_items=5
    )
    signals["Product & Strategy"] = fetch_google_news(
        f'"{company_name}" (launches OR partnership OR expansion OR strategy)', max_items=5
    )
    return signals


# ---------------------------
# LLM SYNTHESIS
# ---------------------------
def build_prompt(company_name, signals):
    signal_text = ""
    for category, items in signals.items():
        if not items:
            continue
        signal_text += f"\n## {category}\n"
        for i, it in enumerate(items, 1):
            signal_text += f"{i}. {it['title']} (Source: {it['source']}, {it['pub_date']})\n"

    prompt = f"""You are an assistant helping a Customer Success Manager (CSM) prepare for
conversations with their enterprise customer: {company_name}.

Below are recent public signals about this company, grouped by category:
{signal_text if signal_text.strip() else "No recent signals were found."}

Using ONLY the signals above, produce a concise daily brief with exactly these sections:

### 1. What's happening inside {company_name}
- 3-5 bullet points, most important/recent first. Each bullet: one sentence, plain language,
  and mention which category it came from in parentheses.

### 2. What you can share with them today
- 2-3 bullet points suggesting a specific, useful, non-generic insight or observation the CSM
  could proactively bring up. Focus on things relevant to a vendor-customer relationship
  (e.g. congratulating a win, flagging a risk, connecting a new hire to a use case).

### 3. Suggested talk track
- Write ONE short sentence (max 30 words) the CSM could literally say to open a conversation,
  referencing the most relevant signal.

If there are no strong signals, say so honestly instead of inventing information.
Do not fabricate facts not present in the signals above."""
    return prompt


def call_groq(prompt, api_key):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500,
        "reasoning_effort": "low",
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------
# UI
# ---------------------------
st.title("🧠 Customer Intelligence Tool")
st.caption("A daily brief for Customer Success Managers — built on free public signals + AI synthesis.")

with st.sidebar:
    st.header("Setup")
    if "GROQ_API_KEY" not in st.secrets:
        st.info("No API key found in secrets. Paste a free Groq key below for this session.")
        manual_key = st.text_input("Groq API Key", type="password")
        if manual_key:
            st.session_state["manual_api_key"] = manual_key
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "1. Enter a customer company name\n"
        "2. The tool pulls recent public news signals\n"
        "3. An LLM synthesizes them into an actionable brief\n\n"
        "*Data sources: Google News RSS (free, public).*"
    )

company_name = st.text_input("Customer company name", placeholder="e.g. Acme Corp")

col1, col2 = st.columns([1, 4])
with col1:
    generate = st.button("Generate Brief", type="primary")

if generate:
    api_key = get_api_key()
    if not company_name.strip():
        st.error("Please enter a company name.")
    elif not api_key:
        st.error("Please provide a Groq API key in the sidebar (free at console.groq.com).")
    else:
        with st.spinner(f"Gathering signals on {company_name}..."):
            signals = collect_signals(company_name)

        total_signals = sum(len(v) for v in signals.values())
        if total_signals == 0:
            st.warning("No public signals found for this company name. Try the full legal/brand name.")
        else:
            with st.spinner("Synthesizing brief with AI..."):
                prompt = build_prompt(company_name, signals)
                try:
                    brief = call_groq(prompt, api_key)
                    st.success(f"Brief generated — {total_signals} signals analyzed")
                    if brief and brief.strip():
                        st.markdown(brief)
                    else:
                        st.warning("The AI returned an empty response. Try clicking Generate Brief again.")
                except Exception as e:
                    st.error(f"AI synthesis failed: {e}")

            st.markdown("---")
            st.subheader("📎 Raw sources used")
            for category, items in signals.items():
                if items:
                    with st.expander(f"{category} ({len(items)})"):
                        for it in items:
                            st.markdown(f"- [{it['title']}]({it['link']}) — *{it['source']}*")

st.markdown("---")
st.caption(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Demo tool, not affiliated with any company mentioned.")# ---------------------------
def fetch_google_news(query, max_items=8):
    """Pull recent news headlines for a query via Google News RSS (no API key needed)."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "Unknown"
            items.append({"title": title, "link": link, "pub_date": pub_date, "source": source})
        return items
    except Exception as e:
        st.warning(f"Could not fetch news for '{query}': {e}")
        return []


def collect_signals(company_name):
    """Collect signals across a few angles that matter to a CSM."""
    signals = {}
    signals["General News"] = fetch_google_news(f'"{company_name}"', max_items=8)
    signals["Leadership & Hiring"] = fetch_google_news(
        f'"{company_name}" (executive OR hire OR appoints OR layoffs OR restructuring)', max_items=5
    )
    signals["Funding & Financials"] = fetch_google_news(
        f'"{company_name}" (funding OR earnings OR acquisition OR revenue)', max_items=5
    )
    signals["Product & Strategy"] = fetch_google_news(
        f'"{company_name}" (launches OR partnership OR expansion OR strategy)', max_items=5
    )
    return signals


# ---------------------------
# LLM SYNTHESIS
# ---------------------------
def build_prompt(company_name, signals):
    signal_text = ""
    for category, items in signals.items():
        if not items:
            continue
        signal_text += f"\n## {category}\n"
        for i, it in enumerate(items, 1):
            signal_text += f"{i}. {it['title']} (Source: {it['source']}, {it['pub_date']})\n"

    prompt = f"""You are an assistant helping a Customer Success Manager (CSM) prepare for
conversations with their enterprise customer: {company_name}.

Below are recent public signals about this company, grouped by category:
{signal_text if signal_text.strip() else "No recent signals were found."}

Using ONLY the signals above, produce a concise daily brief with exactly these sections:

### 1. What's happening inside {company_name}
- 3-5 bullet points, most important/recent first. Each bullet: one sentence, plain language,
  and mention which category it came from in parentheses.

### 2. What you can share with them today
- 2-3 bullet points suggesting a specific, useful, non-generic insight or observation the CSM
  could proactively bring up. Focus on things relevant to a vendor-customer relationship
  (e.g. congratulating a win, flagging a risk, connecting a new hire to a use case).

### 3. Suggested talk track
- Write ONE short sentence (max 30 words) the CSM could literally say to open a conversation,
  referencing the most relevant signal.

If there are no strong signals, say so honestly instead of inventing information.
Do not fabricate facts not present in the signals above."""
    return prompt


def call_groq(prompt, api_key):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        ""max_tokens": 1500,
"reasoning_effort": "low",
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------
# UI
# ---------------------------
st.title("🧠 Customer Intelligence Tool")
st.caption("A daily brief for Customer Success Managers — built on free public signals + AI synthesis.")

with st.sidebar:
    st.header("Setup")
    if "GROQ_API_KEY" not in st.secrets:
        st.info("No API key found in secrets. Paste a free Groq key below for this session.")
        manual_key = st.text_input("Groq API Key", type="password")
        if manual_key:
            st.session_state["manual_api_key"] = manual_key
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "1. Enter a customer company name\n"
        "2. The tool pulls recent public news signals\n"
        "3. An LLM synthesizes them into an actionable brief\n\n"
        "*Data sources: Google News RSS (free, public).*"
    )

company_name = st.text_input("Customer company name", placeholder="e.g. Acme Corp")

col1, col2 = st.columns([1, 4])
with col1:
    generate = st.button("Generate Brief", type="primary")

if generate:
    api_key = get_api_key()
    if not company_name.strip():
        st.error("Please enter a company name.")
    elif not api_key:
        st.error("Please provide a Groq API key in the sidebar (free at console.groq.com).")
    else:
        with st.spinner(f"Gathering signals on {company_name}..."):
            signals = collect_signals(company_name)

        total_signals = sum(len(v) for v in signals.values())
        if total_signals == 0:
            st.warning("No public signals found for this company name. Try the full legal/brand name.")
        else:
            with st.spinner("Synthesizing brief with AI..."):
                prompt = build_prompt(company_name, signals)
                try:
                    brief = call_groq(prompt, api_key)
                st.success(f"Brief generated — {total_signals} signals analyzed")
                if brief and brief.strip():
                    st.markdown(brief)
                else:
                    st.warning("The AI returned an empty response. Try clicking Generate Brief again.")
                except Exception as e:
                    st.error(f"AI synthesis failed: {e}")

            st.markdown("---")
            st.subheader("📎 Raw sources used")
            for category, items in signals.items():
                if items:
                    with st.expander(f"{category} ({len(items)})"):
                        for it in items:
                            st.markdown(f"- [{it['title']}]({it['link']}) — *{it['source']}*")

st.markdown("---")
st.caption(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Demo tool, not affiliated with any company mentioned.")
