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

## <img width="1868" height="923" alt="Screenshot 2026-06-21 141844" src="https://github.com/user-attachments/assets/e425d5d4-1909-4d6e-a0da-a160587eea62" />
##<img width="1895" height="875" alt="Screenshot 2026-06-21 141901" src="https://github.com/user-attachments/assets/915beb4e-68fa-40da-96c4-3b3cc608734a" />
##<img width="1893" height="898" alt="Screenshot 2026-06-21 141922" src="https://github.com/user-attachments/assets/3f7e67ba-22e6-49c4-a3b2-578d4ed24e57" />
##<img width="1875" height="892" alt="Screenshot 2026-06-21 141955" src="https://github.com/user-attachments/assets/e9fa6bc4-9d3b-4c1f-9eb2-8c379b3c7859" />
##<img width="1880" height="801" alt="Screenshot 2026-06-21 142221" src="https://github.com/user-attachments/assets/9f3b7ed9-fb3e-423a-9f8e-97c501683cd9" />



> _Add screenshots/GIFs of the dashboard here (sector tabs, portfolio view, AI analysis panel)._

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
streamlit run app.py
```

---

## 📂 Project Structure

```
stock-market-visualization/
├── app.py                 # Main Streamlit entry point
├── modules/
│   ├── sectors.py          # Sector-wise analysis logic
│   ├── portfolio.py        # Portfolio & holdings view
│   ├── screener.py         # Stock screener logic
│   └── ai_analysis.py      # Claude API integration
├── data/                   # Sample / cached stock data
├── requirements.txt
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

