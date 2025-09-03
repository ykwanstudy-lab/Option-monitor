## Options Greeks Monitor - User Manual (Beginner Friendly)

This app helps you track options and stocks, compute Greeks (Delta, Gamma, Vega, Theta, Rho), monitor P&L, and set alerts for price and delta changes. You don’t need to code to use it.

### 1) Start the app
- Install requirements: `pip install -r requirements.txt`
- Optional (to get live option quotes): Install FutuOpenD and log in on your machine.
- Optional (to receive Telegram alerts): set environment vars:
  - `ENABLE_TELEGRAM=true`
  - `TELEGRAM_BOT_TOKEN=<your_bot_token>`
  - `TELEGRAM_CHAT_ID=<your_chat_id>`
- Run: `python "Option Monitor_Latest.py"`

### 2) Tabs overview
- Positions: Add and manage individual legs (options or stocks)
- Spreads: Combine legs and set alert thresholds (price and delta)
- BS Calculator: Build theoretical positions and compute Greeks using Black–Scholes
- Monitor: Start/stop auto-refresh and set portfolio-wide alerts

### 3) Add a Position
1. Choose Position Type: OPTION or STOCK
2. Market: US or HK
3. Ticker: e.g., AAPL
4. For OPTION: enter Strike, choose Type (CALL/PUT), and Expiry date
5. Quantity: positive = long, negative = short
6. Entry Cost: price you paid per contract (option) or per share (stock)
7. Optional: Alert Remark (your note for alerts)
8. For short STOCK: add Short Interest Rate (%) if you want it deducted
9. Click “Add Position”

Tips:
- Each new position is automatically assigned a leg number.
- Edit or Remove with the buttons under the positions list.

### 4) Create a Spread
1. Go to the Spreads tab
2. Enter a Spread Name
3. Select two or more legs in the list
4. Optionally set Price targets (Upper/Lower) and Delta targets (Upper/Lower)
5. Add an Alert Remark (optional)
6. Click “Add Spread”

You can Edit or Remove spreads later. Spreads are saved to `spreads_config.json`.

### 5) Black–Scholes Calculator
1. Enter a ticker and click “Fetch Market Data” (or type price manually)
2. Add option legs with Strike, DTE (days to expiration), Type, and Quantity
3. Click “Calculate All” to see per-leg and portfolio Greeks and values
4. “Auto-fetch” can periodically refresh the stock price and recalc

### 6) Monitor tab
1. Update Interval (minutes): how often data refreshes
2. P&L % Alerts: set upper/lower percentage thresholds for the whole portfolio
3. Delta Alerts: set upper/lower absolute thresholds for total portfolio delta
4. Save/Load/Clear Saved Data: saves and restores your positions, spreads, and thresholds
5. Click “Start Monitoring” to begin; “Stop Monitoring” to pause

What you’ll see:
- Individual leg data (market price, theoretical BS price, Greeks)
- Running P&L and combined portfolio Greeks
- Alerts printed in the status box

### 7) Alerts
- Spread alerts trigger when the spread price hits targets or delta hits thresholds
- Portfolio alerts trigger on P&L % and delta thresholds
- Console prints all alerts
- If Telegram is configured, alerts are also sent there

### 8) Saving & Restoring
- “Save All Inputs”: stores your positions, spreads, thresholds, and BS inputs in `ui_state.json`
- “Load Saved Inputs”: restores from `ui_state.json`
- “Clear Saved Data”: removes `ui_state.json`, `defaults_config.json`, `spreads_config.json`

### 9) Troubleshooting
- No option quotes? Ensure FutuOpenD is running and you are logged in; otherwise the app still works for stocks and the BS calculator.
- Yahoo price missing? Sometimes Yahoo data is delayed; try again later or check your ticker.
- Telegram not sending? Check `ENABLE_TELEGRAM`, token, and chat ID.

That’s it! Add legs, set alerts, start monitoring.
