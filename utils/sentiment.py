"""
News Sentiment Analysis using Anthropic Claude API.
Fetches recent headlines via yfinance and analyses sentiment.
"""
import json
import os
import requests
import yfinance as yf
import streamlit as st


def fetch_news_headlines(ticker: str, max_items: int = 8) -> list[str]:
    """Fetch recent news headlines for a ticker via yfinance."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        headlines = []
        for item in news[:max_items]:
            title = item.get("content", {}).get("title", "") or item.get("title", "")
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []


def generate_simulated_sentiment(ticker: str, headlines: list[str]) -> dict:
    """Simulate sentiment analysis of headlines based on keyword presence."""
    pos_keywords = ['rise', 'surge', 'gain', 'profit', 'up', 'bull', 'order', 'deal', 'positive', 'highest', 'record', 'growth', 'contract', 'win', 'beat', 'fy26', 'fy25', 'buy', 'dividend', 'expand', 'success']
    neg_keywords = ['fall', 'drop', 'loss', 'down', 'bear', 'negative', 'decline', 'slump', 'deficit', 'warn', 'charges', 'crash', 'sell', 'cut', 'weak']
    
    analyzed_headlines = []
    total_score = 0
    pos_count = 0
    neg_count = 0
    
    for h in headlines:
        h_lower = h.lower()
        has_pos = any(w in h_lower for w in pos_keywords)
        has_neg = any(w in h_lower for w in neg_keywords)
        
        if has_pos and not has_neg:
            sentiment = "Positive"
            score = 25
            reason = "Headline indicators point to positive growth, expansion, or financial gains."
            pos_count += 1
        elif has_neg and not has_pos:
            sentiment = "Negative"
            score = -25
            reason = "Headline references downward trend, loss, or financial pullback."
            neg_count += 1
        else:
            sentiment = "Neutral"
            score = 0
            reason = "General corporate update, news mention, or mixed indicators."
            
        total_score += score
        analyzed_headlines.append({
            "text": h,
            "sentiment": sentiment,
            "reason": reason
        })
        
    num_h = len(headlines)
    avg_score = int((total_score / (num_h * 25)) * 100) if num_h else 0
    
    if avg_score >= 15:
        overall = "Bullish"
    elif avg_score <= -15:
        overall = "Bearish"
    else:
        overall = "Neutral"
        
    summary = f"News sentiment for {ticker} is overall {overall} (Demo Mode). Out of {num_h} headlines analyzed, {pos_count} were positive, {neg_count} negative, and {num_h - pos_count - neg_count} neutral."
    
    return {
        "overall": overall,
        "score": avg_score,
        "summary": summary,
        "headlines": analyzed_headlines
    }


def analyse_sentiment(ticker: str, headlines: list[str]) -> dict:
    """
    Send headlines to Claude and get structured sentiment.
    Returns: {overall, score, summary, headlines_with_sentiment}
    """
    if not headlines:
        return {
            "overall": "Neutral",
            "score": 0,
            "summary": "No recent news found.",
            "headlines": [],
        }

    # API key — Streamlit secrets se lo, fallback environment variable
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    is_placeholder = not api_key or "YAHAN_APNI_REAL_KEY" in api_key or api_key == "sk-ant-api03-YAHAN_APNI_REAL_KEY_PASTE_KARO"

    if is_placeholder:
        return generate_simulated_sentiment(ticker, headlines)

    prompt = f"""You are a financial news sentiment analyst.
Analyse these recent news headlines for the stock ticker: {ticker}

Headlines:
{chr(10).join(f"- {h}" for h in headlines)}

Respond ONLY with a JSON object (no markdown, no backticks):
{{
  "overall": "Bullish" | "Bearish" | "Neutral",
  "score": <integer -100 to 100>,
  "summary": "<2-sentence summary of sentiment>",
  "headlines": [
    {{"text": "<headline>", "sentiment": "Positive" | "Negative" | "Neutral", "reason": "<brief reason>"}}
  ]
}}"""

    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": "claude-3-5-sonnet-latest",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()
        # Strip any accidental fences
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return generate_simulated_sentiment(ticker, headlines)
