## Options Greeks Monitor - Project Overview

Two Python files power the app:
- `Option Monitor_Latest.py`: Graphical app (ttkbootstrap/tkinter). Manages positions, spreads, monitoring, and a built-in BS calculator.
- `futu_options_monitor.py`: Data helpers (Futu + Yahoo), Black–Scholes pricing, portfolio math, alert saving, and Telegram notifications.

### How the app works
1. You add positions (options or stocks) in the GUI. Each is a “leg”.
2. The Monitor tab periodically collects market data:
   - Options: Futu snapshot (if available) + Yahoo underlying price for BS
   - Stocks: Yahoo `regularMarketPrice`
3. For each option leg, the app computes theoretical BS price and shows API Greeks.
4. It then aggregates to a portfolio summary and checks spread- and portfolio-level thresholds.
5. Alerts are printed and optionally sent to Telegram.

### Key modules and functions
- GUI class `OptionsMonitorGUI` (in `Option Monitor_Latest.py`):
  - Tabs setup: positions, spreads, BS calculator, monitor
  - `add_position` / `edit_position` / `remove_position`
  - `add_spread` / `edit_spread` / `remove_spread`
  - `monitor_loop`: fetch data and update UI; calls into `futu_options_monitor`
  - `calculate_spread_metrics`: computes spread price/delta from leg market data
  - BS calculator: `calculate_bs_greeks`, `calculate_bs_portfolio`

- Helpers in `futu_options_monitor.py`:
  - `get_real_option_data(option_code, cache)`: Futu snapshot + Yahoo underlying + BS theoretical price
  - `calculate_and_display_combined_summary(list)`: totals portfolio market value, BS value, P&L, and Greeks
  - `save_alert_data`, `save_spreads_config`, `load_spreads_config`
  - `send_notification(title, msg)`: console + Telegram (if enabled)

### Data persistence
- `input_manager.py` saves and loads your full session to `ui_state.json` (positions, spreads, thresholds, BS inputs)

### Security & configuration
- Set `ENABLE_TELEGRAM=true`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` to enable Telegram alerts
- Futu host/port via `FUTU_HOST` and `FUTU_PORT` (defaults: 127.0.0.1:11111)

### Known limitations
- Without FutuOpenD, option market data isn’t live; stocks and BS still work
- Yahoo Finance can be slow or rate-limited; values may be delayed

See `USER_MANUAL.md` to use the app and `BUGFIXES.md` for important fixes.
