# Futu Combined Options Greeks Monitor - (Futu Options + Yahoo Underlying + BS Theoretical Price + P&L)
# ----------------------------------------------------
# DISCLAIMER:
# This script is for EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY.
# Option data is from FutuOpenD, Underlying stock price is from Yahoo Finance.
# Black-Scholes prices are theoretical and depend on model assumptions.
# P&L calculations are based on user-provided entry costs and current market prices.
# It is NOT financial advice and should NOT be used for actual trading decisions
# without thorough testing and understanding.
# Real financial data and trading involve significant risks.
# You are solely responsible for any use or modification of this script.
# Ensure you understand the FutuOpenAPI terms of service, API limitations,
# and any associated costs before use. Data from Yahoo Finance may have delays.
# ----------------------------------------------------

import time
import pandas as pd
from datetime import datetime
import yfinance as yf
import math # For Black-Scholes calculations
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import json
from pathlib import Path
import os

# --- Configuration ---
CONTRACT_MULTIPLIER = 100 
RISK_FREE_RATE = 0.04  # Placeholder annual risk-free rate (e.g., 3%)

# Telegram Configuration (read from environment for security)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() in ("1", "true", "yes", "on")
if ENABLE_TELEGRAM and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
    print("Telegram enabled but BOT token or CHAT ID missing; disabling notifications.")
    ENABLE_TELEGRAM = False

# Data saving configuration
ALERTS_DIR = "alerts_history"
SPREADS_FILE = "spreads_config.json"
os.makedirs(ALERTS_DIR, exist_ok=True)

# Default threshold settings
DEFAULT_PNL_PCT_THRESHOLD = 5.0  # Default 5% P&L change threshold
DEFAULT_DELTA_THRESHOLD = 50     # Default delta threshold
DEFAULT_SPREAD_TARGET_PRICE_UPPER = None  # Default upper target price (None = no limit)
DEFAULT_SPREAD_TARGET_PRICE_LOWER = None  # Default lower target price (None = no limit)
DEFAULT_SPREAD_DELTA_THRESHOLD = 10   # Default spread delta threshold

# Track previous values for change detection
previous_values = {
    'total_pnl': 0,
    'total_delta': 0,
    'spreads': {}  # Will store previous values for each spread
}

# --- Futu API Connection ---
try:
    from futu import *
    if 'RET_OK' not in globals():
        RET_OK = 0
    # Ensure OptionType exists even if partially imported
    try:
        _ = OptionType.CALL
    except (NameError, AttributeError):
        class OptionType:  # type: ignore
            CALL = 1
            PUT = 2

    HOST = os.getenv('FUTU_HOST', '127.0.0.1')
    PORT = int(os.getenv('FUTU_PORT', '11111'))
    try:
        quote_ctx = OpenQuoteContext(host=HOST, port=PORT)
        if quote_ctx:
            print(f"Successfully connected to FutuOpenD at {HOST}:{PORT}")
        else:
            print(f"Failed to connect to FutuOpenD at {HOST}:{PORT}. Continuing without live quotes.")
            quote_ctx = None
    except Exception as e:
        print(f"Failed to initialize Futu OpenQuoteContext: {e}")
        print("Continuing without live quotes. Some features will be limited.")
        quote_ctx = None
except ImportError:
    print("Futu API library not found. Continuing without live quotes. To enable: pip install futu-api")
    RET_OK = 0
    class OptionType:  # type: ignore
        CALL = 1
        PUT = 2
    quote_ctx = None
except Exception as e:
    print(f"Unexpected error during Futu setup: {e}")
    print("Continuing without live quotes. Some features will be limited.")
    RET_OK = 0
    if 'OptionType' not in globals():
        class OptionType:  # type: ignore
            CALL = 1
            PUT = 2
    quote_ctx = None

# --- Black-Scholes Model ---
def N(x):
    """ Cumulative standard normal distribution function. """
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    """
    Calculates Black-Scholes option price.
    S: Underlying asset price
    K: Strike price
    T: Time to expiration (in years)
    r: Risk-free interest rate (annualized)
    sigma: Volatility (annualized)
    option_type: 'call' or 'put'
    """
    if T <= 0: # Option expired or at expiration
        if option_type.lower() == 'call':
            return max(0, S - K)
        elif option_type.lower() == 'put':
            return max(0, K - S)
        else:
            return 0.0
    
    if sigma <= 0: # Volatility cannot be zero or negative for BS
        print(f"Warning: Sigma (volatility) is {sigma} for S={S}, K={K}, T={T}. Returning intrinsic value.")
        if option_type.lower() == 'call':
            return max(0, S - K)
        elif option_type.lower() == 'put':
            return max(0, K - S)
        else:
            return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type.lower() == 'call':
        price = S * N(d1) - K * math.exp(-r * T) * N(d2)
    elif option_type.lower() == 'put':
        price = K * math.exp(-r * T) * N(-d2) - S * N(-d1)
    else:
        raise ValueError("Option type must be 'call' or 'put'")
    return max(0, price) # Price cannot be negative

# --- Data Fetching Function ---
def get_real_option_data(option_futu_code, underlying_prices_cache):
    if not quote_ctx:
        print("Error: FutuOpenD connection not established.")
        return None

    ret_option, data_option_df = quote_ctx.get_market_snapshot([option_futu_code])
    if ret_option != RET_OK or data_option_df.empty:
        print(f"Error fetching option snapshot for {option_futu_code} from Futu: {ret_option} - {data_option_df}")
        return None
    
    # Add proper error handling for DataFrame access
    try:
        if not isinstance(data_option_df, pd.DataFrame) or data_option_df.empty:
            print(f"Error: Invalid or empty data for {option_futu_code}")
            return None
        option_snapshot = data_option_df.iloc[0]
    except (IndexError, AttributeError) as e:
        print(f"Error accessing data for {option_futu_code}: {e}")
        return None

    option_price = option_snapshot.get('last_price', 0.0)
    strike_price = option_snapshot.get('option_strike_price', 0.0)
    implied_volatility = option_snapshot.get('option_implied_volatility', 0.0) / 100.0 if pd.notna(option_snapshot.get('option_implied_volatility')) else 0.0
    delta = option_snapshot.get('option_delta', 0.0)
    gamma = option_snapshot.get('option_gamma', 0.0)
    vega = option_snapshot.get('option_vega', 0.0)
    theta = option_snapshot.get('option_theta', 0.0)
    rho = option_snapshot.get('option_rho', 0.0)
    option_type_val = option_snapshot.get('option_type', -1)
    option_type_str = "Unknown"
    if option_type_val == OptionType.CALL: option_type_str = 'Call'
    elif option_type_val == OptionType.PUT: option_type_str = 'Put'

    days_to_expiry = 0
    if 'expiry_date_distance' in option_snapshot and pd.notna(option_snapshot['expiry_date_distance']):
        days_to_expiry = int(option_snapshot['expiry_date_distance'])
    elif 'strike_time' in option_snapshot and pd.notna(option_snapshot['strike_time']):
        try:
            expiry_date = datetime.strptime(option_snapshot['strike_time'], "%Y-%m-%d")
            days_to_expiry = (expiry_date - datetime.now()).days
        except ValueError: days_to_expiry = -1

    actual_underlying_price = 0.0
    underlying_stock_code_from_futu = option_snapshot.get('stock_owner', None)
    if underlying_stock_code_from_futu:
        ticker_symbol_parts = underlying_stock_code_from_futu.split('.')
        ticker_symbol = ticker_symbol_parts[-1] if len(ticker_symbol_parts) > 0 else None
        if ticker_symbol:
            if ticker_symbol in underlying_prices_cache:
                actual_underlying_price = underlying_prices_cache[ticker_symbol]
            else:
                print(f"  Fetching underlying price for {ticker_symbol} from Yahoo Finance...")
                try:
                    stock_yf_ticker = yf.Ticker(ticker_symbol)
                    stock_info = stock_yf_ticker.info
                    if 'currentPrice' in stock_info and stock_info['currentPrice'] is not None:
                        actual_underlying_price = stock_info['currentPrice']
                    elif 'regularMarketPrice' in stock_info and stock_info['regularMarketPrice'] is not None:
                        actual_underlying_price = stock_info['regularMarketPrice']
                    elif 'previousClose' in stock_info and stock_info['previousClose'] is not None:
                        actual_underlying_price = stock_info['previousClose']
                        print(f"    (Using previous close for {ticker_symbol} from Yahoo Finance: ${actual_underlying_price:.2f})")
                    else:
                        hist = stock_yf_ticker.history(period="1d", interval="1m")
                        if isinstance(hist, pd.DataFrame) and not hist.empty:
                            actual_underlying_price = hist['Close'].iloc[-1]
                            print(f"    (Using last 1m history close for {ticker_symbol} from Yahoo Finance: ${actual_underlying_price:.2f})")
                        else: print(f"    Could not find price for {ticker_symbol} from Yahoo Finance info or history.")
                    if actual_underlying_price > 0:
                        print(f"    Successfully fetched underlying price for {ticker_symbol} from Yahoo Finance: ${actual_underlying_price:.2f}")
                        underlying_prices_cache[ticker_symbol] = actual_underlying_price
                    else: print(f"    Failed to get a valid price for {ticker_symbol} from Yahoo Finance.")
                except Exception as e: print(f"    Error fetching underlying price for {ticker_symbol} from Yahoo Finance: {e}")
        else: print(f"  Warning: Could not extract ticker from '{underlying_stock_code_from_futu}'")
    else: print(f"  Warning: No 'stock_owner' for {option_futu_code}.")

    theoretical_bs_price = 0.0
    if actual_underlying_price > 0 and strike_price > 0 and implied_volatility > 0 and option_type_str != "Unknown":
        T_years = max(0, days_to_expiry / 365.0) 
        theoretical_bs_price = black_scholes_price(
            S=actual_underlying_price, K=strike_price, T=T_years,
            r=RISK_FREE_RATE, sigma=implied_volatility, option_type=option_type_str
        )
    else:
        print(f"  Skipping BS calculation for {option_futu_code} due to missing inputs (Underlying: {actual_underlying_price}, IV: {implied_volatility})")

    return {"option_code": option_futu_code,"underlying_price": actual_underlying_price, 
            "strike_price": strike_price, "current_option_price": option_price, 
            "volatility": implied_volatility, "interest_rate": RISK_FREE_RATE, 
            "days_to_expiry": days_to_expiry, "option_type": option_type_str, 
            "delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho,
            "theoretical_price_bs": theoretical_bs_price}

# --- Combined Greeks Calculation and Display ---
def calculate_and_display_combined_summary(positions_data_list):
    if not positions_data_list: print("No data for combined summary."); return None 

    net_delta_per_share_equivalent = 0.0
    net_gamma_per_share_equivalent = 0.0
    net_vega_per_share_equivalent = 0.0
    net_theta_per_share_equivalent = 0.0
    net_rho_per_share_equivalent = 0.0
    
    total_market_value, total_theoretical_bs_value, total_pnl = 0.0, 0.0, 0.0
    underlying_price_sum, underlying_price_count = 0.0, 0
    
    total_delta_options = 0.0
    total_delta_stocks = 0.0
    
    print("\n--- Individual Leg Data & P&L (Raw API Values & BS Price) ---")
    for item in positions_data_list:
        greeks_data, quantity, entry_cost = item['greeks_data'], item['quantity'], item['entry_cost']
        # Use option_code for options, ticker for stocks, or 'STOCK' as fallback
        leg_label = greeks_data.get('option_code') or greeks_data.get('ticker') or 'STOCK'
        is_option = bool(greeks_data.get('option_code'))
        multiplier = CONTRACT_MULTIPLIER if is_option else 1
        print(f"  Leg: {leg_label}, Qty: {quantity}, Entry Cost/Share: ${entry_cost:.3f}")
        
        current_market_price = greeks_data['current_option_price']
        leg_pnl = 0.0
        if entry_cost is not None: 
            if quantity > 0: 
                leg_pnl = (current_market_price - entry_cost) * quantity * multiplier
                print(f"    Long position P&L calculation:")
                print(f"    (Current: ${current_market_price:.3f} - Entry: ${entry_cost:.3f}) × Qty: {quantity} × Multiplier: {multiplier} = ${leg_pnl:,.2f}")
            else: 
                leg_pnl = (entry_cost - current_market_price) * abs(quantity) * multiplier
                print(f"    Short position P&L calculation:")
                print(f"    (Entry: ${entry_cost:.3f} - Current: ${current_market_price:.3f}) × |Qty: {quantity}| × Multiplier: {multiplier} = ${leg_pnl:,.2f}")

        # Only print option-specific fields if present
        underlying_price_display = f"${greeks_data['underlying_price']:.2f} (Yahoo)" if 'underlying_price' in greeks_data and greeks_data['underlying_price'] > 0 else "N/A"
        theoretical_bs = greeks_data.get('theoretical_price_bs', 0.0)
        iv = greeks_data.get('volatility', 0.0)
        print(f"    Market OptPrice: ${current_market_price:.3f}, BS OptPrice: ${theoretical_bs:.3f}, Leg P&L: ${leg_pnl:,.2f}")
        print(f"    IV: {iv:.2%}, Underlying: {underlying_price_display}")
        print(f"    API Delta: {greeks_data['delta']:.4f}, API Gamma: {greeks_data['gamma']:.4f}, API Vega: {greeks_data['vega']:.4f}, API Theta: {greeks_data['theta']:.4f}, API Rho: {greeks_data['rho']:.4f}")

        net_delta_per_share_equivalent += greeks_data['delta'] * quantity
        net_gamma_per_share_equivalent += greeks_data['gamma'] * quantity
        net_vega_per_share_equivalent  += greeks_data['vega']  * quantity
        net_theta_per_share_equivalent += greeks_data['theta'] * quantity
        net_rho_per_share_equivalent   += greeks_data['rho']   * quantity
        
        total_market_value += current_market_price * quantity * multiplier
        total_theoretical_bs_value += theoretical_bs * quantity * multiplier
        total_pnl += leg_pnl

        if is_option:
            total_delta_options += greeks_data['delta'] * quantity * CONTRACT_MULTIPLIER
        else:
            total_delta_stocks += greeks_data['delta'] * quantity

        if 'underlying_price' in greeks_data and greeks_data['underlying_price'] > 0:
            underlying_price_sum += greeks_data['underlying_price']
            underlying_price_count +=1
    avg_underlying_price = underlying_price_sum / underlying_price_count if underlying_price_count > 0 else 0.0

    print("\n--- Combined Portfolio Summary ---")
    if avg_underlying_price > 0: print(f"  Average Underlying Price (Yahoo Finance): ${avg_underlying_price:.2f}")
    else: print(f"  Underlying Stock Price: Not fetched or N/A (Yahoo Finance).")
    print(f"  Total Market Value of Positions: ${total_market_value:,.2f}")
    print(f"  Total Theoretical BS Value:      ${total_theoretical_bs_value:,.2f}")
    diff_value = total_market_value - total_theoretical_bs_value
    print(f"  Difference (Market - BS):        ${diff_value:,.2f}")
    print(f"  Total P&L (based on entry costs): ${total_pnl:,.2f}")
    print(f"  Net Delta (per-share equiv.): {net_delta_per_share_equivalent:,.4f}")
    print(f"  Total Delta (options): {total_delta_options:,.2f}")
    print(f"  Total Delta (stocks): {total_delta_stocks:,.2f}")
    print(f"  Total Delta (all): {total_delta_options + total_delta_stocks:,.2f}")
    print(f"  Net Gamma (per-share equiv.): {net_gamma_per_share_equivalent:,.4f} (Total Gamma: {net_gamma_per_share_equivalent * CONTRACT_MULTIPLIER:,.2f})")
    print(f"  Net Vega  (per-share equiv.): {net_vega_per_share_equivalent:,.4f} (Total Vega: {net_vega_per_share_equivalent * CONTRACT_MULTIPLIER:,.2f})")
    print(f"  Net Theta (per-share equiv.): {net_theta_per_share_equivalent:,.4f} (Total Theta: {net_theta_per_share_equivalent * CONTRACT_MULTIPLIER:,.2f})")
    print(f"  Net Rho   (per-share equiv.): {net_rho_per_share_equivalent:,.4f} (Total Rho: {net_rho_per_share_equivalent * CONTRACT_MULTIPLIER:,.2f})")
    print("-----------------------------------")
    
    return {
            "net_delta_per_share_equiv": net_delta_per_share_equivalent,
            "net_gamma_per_share_equiv": net_gamma_per_share_equivalent,
            "net_vega_per_share_equiv": net_vega_per_share_equivalent,
            "net_theta_per_share_equiv": net_theta_per_share_equivalent,
            "net_rho_per_share_equiv": net_rho_per_share_equivalent,
            "total_net_delta": total_delta_options + total_delta_stocks,
            "total_net_gamma": net_gamma_per_share_equivalent * CONTRACT_MULTIPLIER,
            "portfolio_market_value": total_market_value, 
            "portfolio_bs_value": total_theoretical_bs_value,
            "portfolio_pnl": total_pnl,
            "avg_underlying": avg_underlying_price
    }

def save_alert_data(alert_type, alert_data):
    """Save alert data to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{alert_type}_{timestamp}.json"
    filepath = os.path.join(ALERTS_DIR, filename)
    
    data_to_save = {
        "timestamp": datetime.now().isoformat(),
        "type": alert_type,
        "data": alert_data
    }
    
    with open(filepath, 'w') as f:
        json.dump(data_to_save, f, indent=2)
    print(f"Alert data saved to {filepath}")

def load_spreads_config():
    """Load saved spread configurations if they exist."""
    if os.path.exists(SPREADS_FILE):
        with open(SPREADS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_spreads_config(spreads):
    """Save spread configurations for future use."""
    with open(SPREADS_FILE, 'w') as f:
        json.dump(spreads, f, indent=2)
    print(f"Spread configurations saved to {SPREADS_FILE}")

def calculate_spread_metrics(spread, positions):
    """Calculate metrics for a specific spread."""
    spread_legs_data = []
    for leg_num in spread['legs']:
        # Find the position with matching leg number
        leg_position = next((pos for pos in positions if pos['leg_number'] == leg_num), None)
        if leg_position is None:
            return None
        
        # Get current market data for the leg
        option_code = leg_position['option_code']
        ret_option, data_option_df = quote_ctx.get_market_snapshot([option_code])
        if ret_option != RET_OK or data_option_df.empty:
            return None
        
        # Extract market data
        market_data = {
            'option_code': option_code,
            'current_option_price': data_option_df.iloc[0].get('last_price', 0.0),
            'delta': data_option_df.iloc[0].get('option_delta', 0.0)
        }
        
        # Combine position and market data
        spread_legs_data.append({
            'position': leg_position,
            'market_data': market_data
        })
    
    # Calculate combined metrics
    spread_price = 0
    spread_delta = 0
    leg_details = []
    
    for leg_data in spread_legs_data:
        position = leg_data['position']
        market_data = leg_data['market_data']
        
        current_price = market_data['current_option_price']
        quantity = position['quantity']
        
        # Calculate contribution to spread price (per single spread unit)
        # For a spread, we want the net price per spread, not per share
        leg_contribution = current_price * (quantity / abs(quantity)) if quantity != 0 else 0  # Sign based on long/short
        
        # Calculate delta contribution per spread (not per contract)
        # If we have multiple contracts, we want delta per single spread
        delta_per_contract = market_data['delta']
        delta_contribution = delta_per_contract * (quantity / abs(quantity)) if quantity != 0 else 0  # Sign based on long/short
        
        spread_price += leg_contribution
        spread_delta += delta_contribution
        
        leg_details.append({
            'code': market_data['option_code'],
            'price_contribution': leg_contribution,
            'delta_contribution': delta_contribution,
            'quantity': quantity,
            'market_price': current_price,
            'delta': market_data['delta']
        })
    
    return {
        'name': spread['name'],
        'price': spread_price,
        'delta': spread_delta,
        'legs': leg_details,
        'timestamp': datetime.now().isoformat()
    }

def setup_spread_monitoring(positions):
    """Set up spread monitoring with flexible leg combinations."""
    spreads = []
    print("\n--- Spread Monitoring Setup ---")
    print("Available legs:")
    for pos in positions:
        print(f"Leg {pos['leg_number']}: {pos['quantity']}x {pos['option_code']}")
    
    while True:
        spread_choice = input("\nDo you want to monitor any legs as a spread? (y/N): ").strip().lower()
        if spread_choice != 'y':
            break
            
        # Get legs for the spread
        while True:
            try:
                legs_input = input("Enter leg numbers to combine (space-separated, e.g., '3 4'): ").strip()
                leg_numbers = [int(x) for x in legs_input.split()]
                
                # Validate leg numbers
                valid_legs = all(1 <= n <= len(positions) for n in leg_numbers)
                if not valid_legs:
                    print(f"Invalid leg numbers. Please enter numbers between 1 and {len(positions)}.")
                    continue
                    
                # Show selected legs for confirmation
                print("\nSelected legs:")
                for leg_num in leg_numbers:
                    pos = positions[leg_num - 1]
                    print(f"Leg {leg_num}: {pos['quantity']}x {pos['option_code']}")
                
                confirm = input("Confirm these legs? (Y/n): ").strip().lower()
                if confirm in ['', 'y']:
                    break
            except ValueError:
                print("Invalid input. Please enter space-separated numbers.")
        
        # Get spread name and thresholds
        spread_name = input("Enter a name for this spread: ").strip()
        
        # Get target prices
        try:
            print("\nEnter target prices (leave blank for no limit):")
            upper_price = input("Upper target price (e.g., 8.50): ").strip()
            upper_price = float(upper_price) if upper_price else None
            
            lower_price = input("Lower target price (e.g., 6.50): ").strip()
            lower_price = float(lower_price) if lower_price else None
            
            if upper_price is not None and lower_price is not None and upper_price <= lower_price:
                print("Warning: Upper target should be higher than lower target.")
                if not input("Continue anyway? (y/N): ").strip().lower() == 'y':
                    continue
            
            delta_threshold = float(input(f"Enter delta threshold (default {DEFAULT_SPREAD_DELTA_THRESHOLD}): ").strip() or DEFAULT_SPREAD_DELTA_THRESHOLD)
        except ValueError:
            print("Invalid threshold values, using defaults.")
            upper_price = DEFAULT_SPREAD_TARGET_PRICE_UPPER
            lower_price = DEFAULT_SPREAD_TARGET_PRICE_LOWER
            delta_threshold = DEFAULT_SPREAD_DELTA_THRESHOLD
        
        spreads.append({
            'name': spread_name,
            'legs': leg_numbers,
            'target_price_upper': upper_price,
            'target_price_lower': lower_price,
            'delta_threshold': delta_threshold
        })
        print(f"Added spread monitoring for {spread_name}")
        if upper_price is not None or lower_price is not None:
            print(f"Target prices: {lower_price if lower_price is not None else 'None'} to {upper_price if upper_price is not None else 'None'}")
    
    if spreads:
        save_spreads_config(spreads)
    
    return spreads

def check_spread_thresholds(spread_metrics, spread_config):
    """Check if spread metrics exceed their target prices."""
    spread_id = spread_config['name']
    current_price = spread_metrics['price']
    current_delta = spread_metrics['delta']
    delta_change = abs(current_delta - previous_values['spreads'].get(spread_id, {}).get('delta', 0))
    
    alerts = []
    
    # Check if price is outside target range
    if spread_config['target_price_upper'] is not None and abs(current_price) >= spread_config['target_price_upper']:
        price_label = "Debit" if current_price > 0 else "Credit"
        alerts.append(f"Price ${abs(current_price):.3f} {price_label} per spread reached or exceeded upper target ${spread_config['target_price_upper']:.3f}")
    
    if spread_config['target_price_lower'] is not None and abs(current_price) <= spread_config['target_price_lower']:
        price_label = "Debit" if current_price > 0 else "Credit"
        alerts.append(f"Price ${abs(current_price):.3f} {price_label} per spread reached or fell below lower target ${spread_config['target_price_lower']:.3f}")
    
    if delta_change >= spread_config['delta_threshold']:
        alerts.append(f"Delta change: {delta_change:.1f} (threshold: {spread_config['delta_threshold']:.1f})")
    
    if alerts:
        message = f"Spread Alert - {spread_metrics['name']}\n"
        message += "Legs:\n"
        for leg in spread_metrics['legs']:
            message += f"- {leg['code']}: {'Long' if leg['quantity'] > 0 else 'Short'} {abs(leg['quantity'])}x @ ${leg['market_price']:.3f}/share\n"
        message += f"\nSpread Total:\n"
        price_label = "Debit" if current_price > 0 else "Credit"
        message += f"Current Price: ${abs(current_price):.3f} {price_label} per spread\n"
        message += f"Current Delta: {current_delta:.1f}\n"
        if spread_config['target_price_upper'] is not None or spread_config['target_price_lower'] is not None:
            message += f"Target Range: ${spread_config['target_price_lower'] if spread_config['target_price_lower'] is not None else 'None'} to "
            message += f"${spread_config['target_price_upper'] if spread_config['target_price_upper'] is not None else 'None'} per spread\n"
        message += "\nAlerts:\n- " + "\n- ".join(alerts)
        
        # Add custom remark if available
        if spread_config.get('remark'):
            message += f"\n\nRemark: {spread_config['remark']}"
        
        # Save alert data
        alert_data = {
            'spread_name': spread_metrics['name'],
            'spread_metrics': spread_metrics,
            'thresholds': spread_config,
            'alerts': alerts,
            'previous_values': previous_values['spreads'].get(spread_id, {'delta': 0}),
            'changes': {
                'delta_change': delta_change
            },
            'remark': spread_config.get('remark', '')
        }
        save_alert_data('spread', alert_data)
        
        # Send notification
        send_notification(f"Spread Alert - {spread_metrics['name']}", message)
    
    # Update previous values
    previous_values['spreads'][spread_id] = {
        'delta': current_delta
    }

def send_notification(title, message):
    """Send notification to both console and Telegram if enabled."""
    # Always print to console
    print(f"\nALERT: {title}")
    print(message)
    
    # Send to Telegram if enabled
    if ENABLE_TELEGRAM:
        try:
            # Format message for Telegram (using markdown)
            telegram_message = f"*{title}*\n\n{message}"
            
            # Create and run async function to send message
            async def send_telegram():
                try:
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=telegram_message,
                        parse_mode='Markdown'
                    )
                    print("Telegram notification sent successfully")
                except TelegramError as te:
                    print(f"Failed to send Telegram notification: {te}")
                except Exception as e:
                    print(f"Unexpected error sending Telegram notification: {e}")
            
            # Run the async function
            asyncio.run(send_telegram())
        except Exception as e:
            print(f"Error in Telegram notification system: {e}")
            print("Continuing with console notifications only") 