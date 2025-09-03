import json
import os
from typing import Any, Dict


STATE_FILE = "ui_state.json"
DEFAULTS_FILE = "defaults_config.json"
SPREADS_FILE = "spreads_config.json"


class InputManager:
    """Persist and restore app UI state: positions, spreads, and thresholds."""

    def save_all_inputs(self, gui: Any) -> bool:
        try:
            data: Dict[str, Any] = {
                "positions": gui.positions,
                "spreads": gui.spreads,
                "monitor": {
                    "interval": gui.interval_var.get(),
                    "pnl_upper_threshold": gui.pnl_upper_threshold_var.get(),
                    "pnl_lower_threshold": gui.pnl_lower_threshold_var.get(),
                    "pnl_remark": gui.pnl_remark_var.get(),
                    "delta_upper_threshold": gui.delta_upper_threshold_var.get(),
                    "delta_lower_threshold": gui.delta_lower_threshold_var.get(),
                    "delta_remark": gui.delta_remark_var.get(),
                },
                "bs_calculator": {
                    "ticker": gui.bs_ticker_var.get(),
                    "market": gui.bs_market_var.get(),
                    "current_price": gui.bs_current_price_var.get(),
                    "volatility": gui.bs_volatility_var.get(),
                    "risk_free_rate": gui.bs_risk_free_rate_var.get(),
                    "legs": getattr(gui, "bs_legs", []),
                },
            }

            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving UI state: {e}")
            return False

    def load_all_inputs(self, gui: Any) -> bool:
        try:
            if not os.path.exists(STATE_FILE):
                return False

            with open(STATE_FILE, "r") as f:
                data = json.load(f)

            # Restore positions and spreads
            gui.positions = data.get("positions", [])
            gui.spreads = data.get("spreads", [])
            if hasattr(gui, "refresh_positions_tree"):
                gui.refresh_positions_tree()
            if hasattr(gui, "update_legs_listbox"):
                gui.update_legs_listbox()
            if hasattr(gui, "refresh_spreads_tree"):
                gui.refresh_spreads_tree()

            # Restore monitoring thresholds
            monitor = data.get("monitor", {})
            gui.interval_var.set(str(monitor.get("interval", gui.interval_var.get())))
            gui.pnl_upper_threshold_var.set(str(monitor.get("pnl_upper_threshold", gui.pnl_upper_threshold_var.get())))
            gui.pnl_lower_threshold_var.set(str(monitor.get("pnl_lower_threshold", gui.pnl_lower_threshold_var.get())))
            gui.pnl_remark_var.set(str(monitor.get("pnl_remark", gui.pnl_remark_var.get())))
            gui.delta_upper_threshold_var.set(str(monitor.get("delta_upper_threshold", gui.delta_upper_threshold_var.get())))
            gui.delta_lower_threshold_var.set(str(monitor.get("delta_lower_threshold", gui.delta_lower_threshold_var.get())))
            gui.delta_remark_var.set(str(monitor.get("delta_remark", gui.delta_remark_var.get())))

            # Restore BS calculator values
            bs = data.get("bs_calculator", {})
            gui.bs_ticker_var.set(bs.get("ticker", gui.bs_ticker_var.get()))
            gui.bs_market_var.set(bs.get("market", gui.bs_market_var.get()))
            gui.bs_current_price_var.set(bs.get("current_price", gui.bs_current_price_var.get()))
            gui.bs_volatility_var.set(bs.get("volatility", gui.bs_volatility_var.get()))
            gui.bs_risk_free_rate_var.set(bs.get("risk_free_rate", gui.bs_risk_free_rate_var.get()))
            gui.bs_legs = bs.get("legs", getattr(gui, "bs_legs", []))
            if hasattr(gui, "calculate_bs_portfolio"):
                gui.calculate_bs_portfolio()

            return True
        except Exception as e:
            print(f"Error loading UI state: {e}")
            return False

    def clear_all_inputs(self) -> bool:
        try:
            for path in (STATE_FILE, DEFAULTS_FILE, SPREADS_FILE):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as e:
                    print(f"Failed to remove {path}: {e}")
            return True
        except Exception as e:
            print(f"Error clearing inputs: {e}")
            return False

