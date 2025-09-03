## Bug Fixes and Improvements

### 1) Hard-coded Telegram token (SECURITY)
- Issue: Plaintext token and chat ID were embedded in `futu_options_monitor.py`.
- Fix: Read `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `ENABLE_TELEGRAM` from environment. If missing, disable Telegram gracefully.

### 2) Crashing on Futu import or connection
- Issue: Script exited if Futu library wasn’t installed or OpenD wasn’t reachable.
- Fix: Convert to soft dependency. Continue without live quotes; features degrade gracefully. Added `FUTU_HOST`/`FUTU_PORT` env vars.

### 3) Rebinding Tk variables (GUI state loss)
- Issue: In the Monitor tab, the code re-created `StringVar` instances, breaking saved/default values.
- Fix: Reuse existing `StringVar` instances instead of overwriting them.

### 4) Wrong P&L percentage base for stocks
- Issue: Portfolio P&L % baseline multiplied every leg by the options contract multiplier (100), including stocks.
- Fix: Use multiplier 100 for options and 1 for stocks.

### 5) Missing `InputManager` implementation
- Issue: The GUI referenced `InputManager` but the module didn’t exist.
- Fix: Implemented `input_manager.py` to save/load/clear `ui_state.json` with positions, spreads, thresholds, and BS inputs.

### 6) Safer spread and monitoring behavior when data is unavailable
- Improvement: Many calls now handle missing quotes (no Futu/no Yahoo) without crashing; warnings are shown and UI continues.

Refer to the git diff for exact edits.
