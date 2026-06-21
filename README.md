# 📊 Indian Stock Market Dashboard

An interactive **Streamlit-based stock market dashboard** for tracking, analyzing, and paper-trading Indian equities — with sector-wise insights and AI-powered analysis.

---

## 🚀 Features

- **Sector Analysis Tabs** — Dedicated views for Defence, Broking, Renewable Energy, and EV & Auto Tech sectors
- **Zerodha-style Portfolio View** — Clean, familiar UI for tracking holdings and positions
- **Paper Trading** — Simulate buy/sell trades without real money to test strategies
- **P&L Reporting** — Real-time profit & loss tracking across trades and holdings
- **Stock Screener** — Filter and shortlist stocks based on custom criteria
- **AI-Powered Analysis** — Integrated with the Claude API to generate natural-language insights on stocks and sectors

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend / App Framework | Streamlit |
| Language | Python |
| AI Integration | Claude API (Anthropic) |
| Data Handling | Pandas |
| Visualization | Plotly / Matplotlib |

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><b>Portfolio View</b><br/>Zerodha-style holdings, P&L tracking, and quick-access module bar</td>
    <td align="center"><b>Sector Dashboard — Defence</b><br/>India Defence Budget & Order Tracker with FY22–FY26 trend analysis</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/1f51f605-b713-43bf-a1e5-6424a2126477" width="420"/></td>
    <td><img src="https://github.com/user-attachments/assets/5bdfc091-69fa-4968-9154-8de0e3b592d9" width="420"/></td>
  </tr>
  <tr>
    <td align="center"><b>Stock Screener</b><br/>Filter stocks by P/E, volume, 52W range, and sector</td>
    <td align="center"><b>Market Overview</b><br/>Live indices, economic calendar, and sector navigation</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c29bcb3d-ad91-45a3-b410-43de33a91fe8" width="420"/></td>
    <td><img src="https://github.com/user-attachments/assets/f7d94250-c3a2-48fd-b206-e5cc3b100858" width="420"/></td>
  </tr>
</table>

---

## ⚙️ Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/Nitinrajgor07/stock-market-visualization.git
cd stock-market-visualization

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Claude API key
# Create a .env file in the root directory:
# ANTHROPIC_API_KEY=your_api_key_here

# 5. Run the app
streamlit run main.py
```

---

## 📂 Project Structure

```
stock-market-visualization/
├── main.py                # Main Streamlit entry point
├── analytics.py            # Stock analytics & calculations
├── data_fetcher.py         # Fetches market/stock data
├── ml_predictor.py         # ML-based price prediction logic
├── portfolio.py             # Portfolio & holdings management
├── sentiment.py             # Sentiment analysis module
├── visualizations.py        # Charts & visualization logic
├── portfolio_data.json      # Stored portfolio data
├── stock_data.csv           # Sample stock dataset
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🧠 How It Works

1. User selects a sector or stock from the dashboard.
2. Live/historical data is fetched and processed using Pandas.
3. The dashboard renders interactive charts (price trends, volume, P&L).
4. On request, the Claude API analyzes the selected stock/sector and returns a plain-language summary or recommendation.
5. Users can simulate trades via the paper trading module and track performance over time.

---

## 🔮 Future Improvements

- Real-time price feed integration (e.g., NSE/BSE APIs)
- User authentication for personalized portfolios
- Export reports as PDF/Excel
- Mobile-responsive layout

---

## 👤 Author

**Nitin Rajgor**
M.Sc. CS & IT, Jain University, Bengaluru
📧 rajgornitin2308@gmail.com

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
