"""
News Sentiment Analysis using Anthropic Claude API.
Fetches recent headlines from yfinance and analyses sentiment.
"""
import json
import requests
import yfinance as yf


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


def analyse_sentiment(ticker: str, headlines: list[str]) -> dict:
    """
    Send headlines to Claude claude-sonnet-4-20250514 and get structured sentiment.
    Returns: {overall, score, summary, headlines_with_sentiment}
    """
    if not headlines:
        return {
            "overall": "Neutral",
            "score": 0,
            "summary": "No recent news found.",
            "headlines": [],
        }

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
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
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
        return {
            "overall": "Neutral",
            "score": 0,
            "summary": f"Sentiment analysis unavailable: {e}",
            "headlines": [{"text": h, "sentiment": "Neutral", "reason": ""} for h in headlines],
        }
