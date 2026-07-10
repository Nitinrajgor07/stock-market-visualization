import json
import os

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio_data.json")
OUTPUT_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdings.json")


def main():
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERROR: portfolio_data.json nahi mili. Pehle Streamlit app chalao aur kuch BUY karo.")
        return
    except Exception as e:
        print(f"ERROR reading portfolio_data.json: {e}")
        return

    holdings = data.get("pt_holdings", {})
    if not holdings:
        print("WARNING: Koi holdings nahi mili portfolio_data.json mein.")
        return

    clean_holdings = {}
    for ticker, h in holdings.items():
        clean_holdings[ticker] = {
            "shares": h.get("shares", 0),
            "avg_price": h.get("avg_price", 0.0),
            "first_buy_date": h.get("first_buy_date"),
        }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(clean_holdings, f, indent=2)

    print(f"SUCCESS: holdings.json ban gayi - {len(clean_holdings)} holdings sync ho gayi.")
    print("Ab is file ko Telegram-bot GitHub repo mein push karo.")


if __name__ == "__main__":
    main()
