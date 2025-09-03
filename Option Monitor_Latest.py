# To change the color theme, just change the themename below (e.g., 'flatly', 'sandstone', 'yeti', 'minty', 'cosmo', etc.)
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap import Style
import tkinter as tk  # Only for tk.Listbox and tk constants
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from datetime import datetime, date
import futu_options_monitor as monitor
from ttkbootstrap.widgets import DateEntry
import json
import os
from input_manager import InputManager
import math
import yfinance as yf

# Configuration files for saving defaults
DEFAULTS_FILE = "defaults_config.json"
POSITION_DEFAULTS_FILE = "position_defaults.json"

# Constants for BS Calculator
CONTRACT_MULTIPLIER = 100

# Black-Scholes functions
def N(x):
    """Cumulative standard normal distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    """Calculate Black-Scholes option price."""
    if T <= 0:
        if option_type.lower() == 'call':
            return max(0, S - K)
        elif option_type.lower() == 'put':
            return max(0, K - S)
        else:
            return 0.0
    
    if sigma <= 0:
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
    return max(0, price)

class OptionsMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Options Greeks Monitor")
        self.root.geometry("1200x800")  # Set larger window size
        self.root.minsize(1000, 700)    # Set minimum size
        self.positions = []
        self.spreads = []
        self.monitoring = False
        
        # Initialize input manager
        self.input_manager = InputManager()
        
        # Initialize previous values dictionary
        self.previous_values = {
            'total_pnl': 0,
            'total_delta': 0,
            'spreads': {}
        }
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.positions_frame = ttk.Frame(self.notebook)
        self.spreads_frame = ttk.Frame(self.notebook)
        self.bs_calculator_frame = ttk.Frame(self.notebook)
        self.monitor_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.positions_frame, text='Positions')
        self.notebook.add(self.spreads_frame, text='Spreads')
        self.notebook.add(self.bs_calculator_frame, text='BS Calculator')
        self.notebook.add(self.monitor_frame, text='Monitor')
        
        # Initialize StringVar variables
        self.market_var = tk.StringVar(value="US")
        self.ticker_var = tk.StringVar()
        self.strike_var = tk.StringVar()
        self.option_type_var = tk.StringVar(value="CALL")
        self.expiry_var = tk.StringVar()
        self.quantity_var = tk.StringVar()
        self.entry_cost_var = tk.StringVar()
        self.position_remark_var = tk.StringVar()  # New: position alert remark
        self.spread_name_var = tk.StringVar()
        self.current_price_var = tk.StringVar(value="N/A")
        self.current_delta_var = tk.StringVar(value="N/A")
        self.upper_target_var = tk.StringVar()
        self.lower_target_var = tk.StringVar()
        self.upper_delta_target_var = tk.StringVar()
        self.lower_delta_target_var = tk.StringVar()
        self.spread_remark_var = tk.StringVar()  # New: spread alert remark
        self.interval_var = tk.StringVar(value="15")
        self.pnl_upper_threshold_var = tk.StringVar(value="")  # New P&L upper threshold
        self.pnl_lower_threshold_var = tk.StringVar(value="")  # New P&L lower threshold
        self.pnl_remark_var = tk.StringVar(value="")  # New P&L remark
        self.delta_upper_threshold_var = tk.StringVar(value="")  # New delta upper threshold
        self.delta_lower_threshold_var = tk.StringVar(value="")  # New delta lower threshold
        self.delta_remark_var = tk.StringVar(value="")  # New delta remark
        
        # Initialize BS Calculator variables
        self.bs_legs = []
        self.bs_ticker_var = tk.StringVar()
        self.bs_market_var = tk.StringVar(value="US")
        self.bs_current_price_var = tk.StringVar(value="0.00")
        self.bs_volatility_var = tk.StringVar(value="0.20")
        self.bs_risk_free_rate_var = tk.StringVar(value="0.04")
        self.bs_auto_fetch_var = tk.BooleanVar(value=True)
        
        # Load saved defaults
        self.load_defaults()
        
        self.setup_positions_tab()
        self.setup_spreads_tab()
        self.setup_bs_calculator_tab()
        self.setup_monitor_tab()
        
        # Load saved inputs automatically
        self.input_manager.load_all_inputs(self)
    
    def load_defaults(self):
        """Load saved default values for inputs."""
        try:
            if os.path.exists(DEFAULTS_FILE):
                with open(DEFAULTS_FILE, 'r') as f:
                    defaults = json.load(f)
                    
                # Load position defaults
                if 'position' in defaults:
                    pos_defaults = defaults['position']
                    self.market_var.set(pos_defaults.get('market', 'US'))
                    self.ticker_var.set(pos_defaults.get('ticker', ''))
                    self.strike_var.set(pos_defaults.get('strike', ''))
                    self.option_type_var.set(pos_defaults.get('option_type', 'CALL'))
                    self.quantity_var.set(pos_defaults.get('quantity', ''))
                    self.entry_cost_var.set(pos_defaults.get('entry_cost', ''))
                    self.position_remark_var.set(pos_defaults.get('remark', ''))
                
                # Load monitoring defaults
                if 'monitor' in defaults:
                    monitor_defaults = defaults['monitor']
                    self.interval_var.set(str(monitor_defaults.get('interval', '15')))
                    self.pnl_upper_threshold_var.set(str(monitor_defaults.get('pnl_upper_threshold', '')))
                    self.pnl_lower_threshold_var.set(str(monitor_defaults.get('pnl_lower_threshold', '')))
                    self.pnl_remark_var.set(str(monitor_defaults.get('pnl_remark', '')))
                    self.delta_upper_threshold_var.set(str(monitor_defaults.get('delta_upper_threshold', '')))
                    self.delta_lower_threshold_var.set(str(monitor_defaults.get('delta_lower_threshold', '')))
                    self.delta_remark_var.set(str(monitor_defaults.get('delta_remark', '')))
                
                # Load spread defaults
                if 'spread' in defaults:
                    spread_defaults = defaults['spread']
                    self.upper_target_var.set(spread_defaults.get('upper_target', ''))
                    self.lower_target_var.set(spread_defaults.get('lower_target', ''))
                    self.upper_delta_target_var.set(spread_defaults.get('upper_delta_target', ''))
                    self.lower_delta_target_var.set(spread_defaults.get('lower_delta_target', ''))
                    self.spread_remark_var.set(spread_defaults.get('remark', ''))
                    
        except Exception as e:
            print(f"Error loading defaults: {e}")
    
    def save_defaults(self):
        """Save current input values as defaults."""
        defaults = {
            'position': {
                'market': self.market_var.get(),
                'ticker': self.ticker_var.get(),
                'strike': self.strike_var.get(),
                'option_type': self.option_type_var.get(),
                'quantity': self.quantity_var.get(),
                'entry_cost': self.entry_cost_var.get(),
                'remark': self.position_remark_var.get()
            },
            'monitor': {
                'interval': self.interval_var.get(),
                'pnl_upper_threshold': self.pnl_upper_threshold_var.get(),
                'pnl_lower_threshold': self.pnl_lower_threshold_var.get(),
                'pnl_remark': self.pnl_remark_var.get(),
                'delta_upper_threshold': self.delta_upper_threshold_var.get(),
                'delta_lower_threshold': self.delta_lower_threshold_var.get(),
                'delta_remark': self.delta_remark_var.get()
            },
            'spread': {
                'upper_target': self.upper_target_var.get(),
                'lower_target': self.lower_target_var.get(),
                'upper_delta_target': self.upper_delta_target_var.get(),
                'lower_delta_target': self.lower_delta_target_var.get(),
                'remark': self.spread_remark_var.get()
            }
        }
        
        try:
            with open(DEFAULTS_FILE, 'w') as f:
                json.dump(defaults, f, indent=2)
        except Exception as e:
            print(f"Error saving defaults: {e}")
    
    def save_all_inputs(self):
        """Save all current inputs."""
        if self.input_manager.save_all_inputs(self):
            messagebox.showinfo("Success", "All inputs saved successfully!\nThey will be restored when you restart the program.")
        else:
            messagebox.showerror("Error", "Failed to save inputs.")
    
    def load_all_inputs(self):
        """Load all saved inputs."""
        if self.input_manager.load_all_inputs(self):
            messagebox.showinfo("Success", "All saved inputs loaded successfully!")
        else:
            messagebox.showwarning("Warning", "No saved inputs found or failed to load.")
    
    def clear_saved_data(self):
        """Clear all saved data."""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all saved data?\nThis cannot be undone."):
            if self.input_manager.clear_all_inputs():
                messagebox.showinfo("Success", "All saved data cleared successfully!")
            else:
                messagebox.showerror("Error", "Failed to clear saved data.")
    
    def setup_positions_tab(self):
        # Position input frame
        input_frame = ttk.LabelFrame(self.positions_frame, text="Add New Position")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Position type selection
        ttk.Label(input_frame, text="Position Type:").grid(row=0, column=0, padx=5, pady=5)
        self.position_type_var = tk.StringVar(value="OPTION")
        position_type_combo = ttk.Combobox(input_frame, textvariable=self.position_type_var, 
                                         values=["OPTION", "STOCK"], state="readonly")
        position_type_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Market selection
        ttk.Label(input_frame, text="Market:").grid(row=0, column=2, padx=5, pady=5)
        market_combo = ttk.Combobox(input_frame, textvariable=self.market_var, values=["US", "HK"], state="readonly")
        market_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # Ticker input
        ttk.Label(input_frame, text="Ticker:").grid(row=1, column=0, padx=5, pady=5)
        ticker_entry = ttk.Entry(input_frame, textvariable=self.ticker_var)
        ticker_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Strike price input (for options only)
        self.strike_label = ttk.Label(input_frame, text="Strike Price:")
        self.strike_label.grid(row=1, column=2, padx=5, pady=5)
        strike_entry = ttk.Entry(input_frame, textvariable=self.strike_var)
        strike_entry.grid(row=1, column=3, padx=5, pady=5)
        
        # Option type selection (for options only)
        self.option_type_label = ttk.Label(input_frame, text="Option Type:")
        self.option_type_label.grid(row=2, column=0, padx=5, pady=5)
        option_type_combo = ttk.Combobox(input_frame, textvariable=self.option_type_var, values=["CALL", "PUT"], state="readonly")
        option_type_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Expiry date selection (for options only)
        self.expiry_label = ttk.Label(input_frame, text="Expiry Date:")
        self.expiry_label.grid(row=2, column=2, padx=5, pady=5)
        self.expiry_entry = DateEntry(input_frame, dateformat='%Y-%m-%d')
        self.expiry_entry.grid(row=2, column=3, padx=5, pady=5)
        
        # Quantity input
        ttk.Label(input_frame, text="Quantity:").grid(row=3, column=0, padx=5, pady=5)
        quantity_entry = ttk.Entry(input_frame, textvariable=self.quantity_var)
        quantity_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Entry cost input
        ttk.Label(input_frame, text="Entry Cost:").grid(row=3, column=2, padx=5, pady=5)
        entry_cost_entry = ttk.Entry(input_frame, textvariable=self.entry_cost_var)
        entry_cost_entry.grid(row=3, column=3, padx=5, pady=5)
        
        # Short interest rate input (for short stock only)
        self.short_rate_label = ttk.Label(input_frame, text="Short Interest Rate (%):")
        self.short_rate_label.grid(row=4, column=0, padx=5, pady=5)
        self.short_rate_var = tk.StringVar(value="0.0")
        short_rate_entry = ttk.Entry(input_frame, textvariable=self.short_rate_var)
        short_rate_entry.grid(row=4, column=1, padx=5, pady=5)
        
        # Alert remark input
        ttk.Label(input_frame, text="Alert Remark:").grid(row=4, column=2, padx=5, pady=5)
        remark_entry = ttk.Entry(input_frame, textvariable=self.position_remark_var, width=40)
        remark_entry.grid(row=4, column=3, padx=5, pady=5, sticky='ew')
        
        # Update position type visibility
        def update_position_type(*args):
            is_option = self.position_type_var.get() == "OPTION"
            self.strike_label.grid() if is_option else self.strike_label.grid_remove()
            strike_entry.grid() if is_option else strike_entry.grid_remove()
            self.option_type_label.grid() if is_option else self.option_type_label.grid_remove()
            option_type_combo.grid() if is_option else option_type_combo.grid_remove()
            self.expiry_label.grid() if is_option else self.expiry_label.grid_remove()
            self.expiry_entry.grid() if is_option else self.expiry_entry.grid_remove()
            
            # Show/hide short rate input based on position type and quantity
            try:
                quantity = int(self.quantity_var.get())
                is_short = quantity < 0
                is_stock = self.position_type_var.get() == "STOCK"
                self.short_rate_label.grid() if (is_stock and is_short) else self.short_rate_label.grid_remove()
                short_rate_entry.grid() if (is_stock and is_short) else short_rate_entry.grid_remove()
            except:
                self.short_rate_label.grid_remove()
                short_rate_entry.grid_remove()
        
        self.position_type_var.trace('w', update_position_type)
        self.quantity_var.trace('w', update_position_type)
        update_position_type()  # Initial update
        
        # Button frame for Add Position and Save as Default
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=5, column=0, columnspan=4, pady=10)
        
        # Add position button
        ttk.Button(button_frame, text="Add Position", command=self.add_position).pack(side=tk.LEFT, padx=5)
        
        # Save as default button
        ttk.Button(button_frame, text="Save as Default", command=self.save_defaults).pack(side=tk.LEFT, padx=5)
        
        # Positions list
        list_frame = ttk.LabelFrame(self.positions_frame, text="Current Positions")
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create a frame for the treeview with scrollbar
        pos_tree_frame = ttk.Frame(list_frame)
        pos_tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Treeview for positions
        self.positions_tree = ttk.Treeview(pos_tree_frame, columns=("Leg", "Market", "Ticker", "Strike", "Type", "Expiry", "Quantity", "Cost", "Remark"), show="headings", height=6)
        self.positions_tree.heading("Leg", text="Leg")
        self.positions_tree.heading("Market", text="Market")
        self.positions_tree.heading("Ticker", text="Ticker")
        self.positions_tree.heading("Strike", text="Strike")
        self.positions_tree.heading("Type", text="Type")
        self.positions_tree.heading("Expiry", text="Expiry")
        self.positions_tree.heading("Quantity", text="Quantity")
        self.positions_tree.heading("Cost", text="Cost")
        self.positions_tree.heading("Remark", text="Alert Remark")
        
        # Set column widths
        self.positions_tree.column("Leg", width=50)
        self.positions_tree.column("Market", width=60)
        self.positions_tree.column("Ticker", width=80)
        self.positions_tree.column("Strike", width=80)
        self.positions_tree.column("Type", width=60)
        self.positions_tree.column("Expiry", width=100)
        self.positions_tree.column("Quantity", width=80)
        self.positions_tree.column("Cost", width=80)
        self.positions_tree.column("Remark", width=150)
        
        # Add scrollbar for the positions treeview
        pos_scrollbar = ttk.Scrollbar(pos_tree_frame, orient="vertical", command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.positions_tree.pack(side="left", fill='both', expand=True)
        pos_scrollbar.pack(side="right", fill="y")
        
        # Position management buttons - place at bottom, always visible
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(side='bottom', pady=10, fill='x')
        
        # Center the buttons
        pos_button_container = ttk.Frame(button_frame)
        pos_button_container.pack(expand=True)
        
        ttk.Button(pos_button_container, text="Edit Selected Position", command=self.edit_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(pos_button_container, text="Remove Selected Position", command=self.remove_position).pack(side=tk.LEFT, padx=5)
    
    def setup_spreads_tab(self):
        # Spread input frame
        input_frame = ttk.LabelFrame(self.spreads_frame, text="Add New Spread")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Spread name input
        ttk.Label(input_frame, text="Spread Name:").grid(row=0, column=0, padx=5, pady=5)
        spread_name_entry = ttk.Entry(input_frame, textvariable=self.spread_name_var)
        spread_name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        
        # Legs selection and alert settings in a more compact layout
        ttk.Label(input_frame, text="Select Legs:").grid(row=1, column=0, padx=5, pady=5, sticky='nw')
        self.legs_listbox = tk.Listbox(input_frame, selectmode=tk.MULTIPLE, height=4)
        self.legs_listbox.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        # Alert settings on the right side
        alerts_frame = ttk.Frame(input_frame)
        alerts_frame.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky='new')
        
        # Price threshold frame - compact
        price_frame = ttk.LabelFrame(alerts_frame, text="Price Alerts")
        price_frame.pack(fill='x', pady=2)
        
        # Upper price target
        upper_price_row = ttk.Frame(price_frame)
        upper_price_row.pack(fill='x', padx=5, pady=2)
        ttk.Label(upper_price_row, text="Upper:", width=8).pack(side=tk.LEFT)
        ttk.Entry(upper_price_row, textvariable=self.upper_target_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(upper_price_row, text="Clear", width=6,
                   command=lambda: self.upper_target_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Lower price target
        lower_price_row = ttk.Frame(price_frame)
        lower_price_row.pack(fill='x', padx=5, pady=2)
        ttk.Label(lower_price_row, text="Lower:", width=8).pack(side=tk.LEFT)
        ttk.Entry(lower_price_row, textvariable=self.lower_target_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(lower_price_row, text="Clear", width=6,
                   command=lambda: self.lower_target_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Delta threshold frame - compact
        delta_frame = ttk.LabelFrame(alerts_frame, text="Delta Alerts")
        delta_frame.pack(fill='x', pady=2)
        
        # Upper delta target
        upper_delta_row = ttk.Frame(delta_frame)
        upper_delta_row.pack(fill='x', padx=5, pady=2)
        ttk.Label(upper_delta_row, text="Upper:", width=8).pack(side=tk.LEFT)
        ttk.Entry(upper_delta_row, textvariable=self.upper_delta_target_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(upper_delta_row, text="Clear", width=6,
                   command=lambda: self.upper_delta_target_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Lower delta target
        lower_delta_row = ttk.Frame(delta_frame)
        lower_delta_row.pack(fill='x', padx=5, pady=2)
        ttk.Label(lower_delta_row, text="Lower:", width=8).pack(side=tk.LEFT)
        ttk.Entry(lower_delta_row, textvariable=self.lower_delta_target_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(lower_delta_row, text="Clear", width=6,
                   command=lambda: self.lower_delta_target_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Alert remark frame - below legs
        remark_frame = ttk.LabelFrame(input_frame, text="Alert Remark")
        remark_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky='ew')
        
        ttk.Label(remark_frame, text="Custom Alert Message:").pack(anchor='w', padx=5, pady=2)
        remark_entry = ttk.Entry(remark_frame, textvariable=self.spread_remark_var, width=50)
        remark_entry.pack(fill='x', padx=5, pady=2)
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=5)
        
        # Reset spread button
        ttk.Button(button_frame, text="Reset Spread", 
                  command=self.reset_spread).pack(side=tk.LEFT, padx=5)
        
        # Add spread button
        ttk.Button(button_frame, text="Add Spread", 
                  command=self.add_spread).pack(side=tk.LEFT, padx=5)
        
        # Save as default button
        ttk.Button(button_frame, text="Save as Default", 
                  command=self.save_defaults).pack(side=tk.LEFT, padx=5)
        
        # Spreads list
        list_frame = ttk.LabelFrame(self.spreads_frame, text="Current Spreads")
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create a frame for the treeview with scrollbar
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Treeview for spreads (combine upper/lower targets)
        self.spreads_tree = ttk.Treeview(tree_frame, columns=("Name", "Legs", "Price Target", "Delta Threshold", "Remark"), show="headings", height=6)
        self.spreads_tree.heading("Name", text="Name")
        self.spreads_tree.heading("Legs", text="Legs")
        self.spreads_tree.heading("Price Target", text="Price Target")
        self.spreads_tree.heading("Delta Threshold", text="Delta Threshold")
        self.spreads_tree.heading("Remark", text="Alert Remark")
        
        # Set column widths
        self.spreads_tree.column("Name", width=120)
        self.spreads_tree.column("Legs", width=100)
        self.spreads_tree.column("Price Target", width=120)
        self.spreads_tree.column("Delta Threshold", width=120)
        self.spreads_tree.column("Remark", width=200)
        
        # Add scrollbar for the treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.spreads_tree.yview)
        self.spreads_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.spreads_tree.pack(side="left", fill='both', expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Spread management buttons - place at bottom of list_frame, not expanding
        spread_button_frame = ttk.Frame(list_frame)
        spread_button_frame.pack(side='bottom', pady=10, fill='x')
        
        # Center the buttons
        button_container = ttk.Frame(spread_button_frame)
        button_container.pack(expand=True)
        
        ttk.Button(button_container, text="Edit Selected Spread", command=self.edit_spread).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text="Remove Selected Spread", command=self.remove_spread).pack(side=tk.LEFT, padx=5)
    
    def setup_bs_calculator_tab(self):
        # Main container with scrollable frame
        main_container = ttk.Frame(self.bs_calculator_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left panel for inputs and controls
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side='left', fill='y', padx=(0, 5))
        
        # Right panel for results
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # === LEFT PANEL: INPUTS ===
        
        # Market data input frame
        market_frame = ttk.LabelFrame(left_panel, text="Market Data")
        market_frame.pack(fill='x', pady=(0, 5))
        
        # Market selection
        ttk.Label(market_frame, text="Market:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        market_combo = ttk.Combobox(market_frame, textvariable=self.bs_market_var, values=["US", "HK"], state="readonly", width=10)
        market_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Ticker input
        ttk.Label(market_frame, text="Ticker:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ticker_entry = ttk.Entry(market_frame, textvariable=self.bs_ticker_var, width=15)
        ticker_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Auto-fetch checkbox
        auto_fetch_cb = ttk.Checkbutton(market_frame, text="Auto-fetch data", variable=self.bs_auto_fetch_var)
        auto_fetch_cb.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # Fetch button
        ttk.Button(market_frame, text="Fetch Market Data", command=self.fetch_bs_market_data).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Market parameters frame
        params_frame = ttk.LabelFrame(left_panel, text="Market Parameters")
        params_frame.pack(fill='x', pady=(0, 5))
        
        # Current stock price
        ttk.Label(params_frame, text="Stock Price ($):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        price_entry = ttk.Entry(params_frame, textvariable=self.bs_current_price_var, width=15)
        price_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Volatility
        ttk.Label(params_frame, text="Volatility:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        vol_entry = ttk.Entry(params_frame, textvariable=self.bs_volatility_var, width=15)
        vol_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Risk-free rate
        ttk.Label(params_frame, text="Risk-free Rate:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        rate_entry = ttk.Entry(params_frame, textvariable=self.bs_risk_free_rate_var, width=15)
        rate_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Option leg input frame
        leg_frame = ttk.LabelFrame(left_panel, text="Add Option Leg")
        leg_frame.pack(fill='x', pady=(0, 5))
        
        # Strike price
        ttk.Label(leg_frame, text="Strike ($):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.bs_strike_var = tk.StringVar()
        strike_entry = ttk.Entry(leg_frame, textvariable=self.bs_strike_var, width=15)
        strike_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Days to expiration
        ttk.Label(leg_frame, text="DTE (days):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.bs_dte_var = tk.StringVar()
        dte_entry = ttk.Entry(leg_frame, textvariable=self.bs_dte_var, width=15)
        dte_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Option type
        ttk.Label(leg_frame, text="Type:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.bs_option_type_var = tk.StringVar(value="CALL")
        type_combo = ttk.Combobox(leg_frame, textvariable=self.bs_option_type_var, values=["CALL", "PUT"], state="readonly", width=12)
        type_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Quantity
        ttk.Label(leg_frame, text="Quantity:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.bs_quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(leg_frame, textvariable=self.bs_quantity_var, width=15)
        quantity_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Add leg button
        ttk.Button(leg_frame, text="Add Leg", command=self.add_bs_leg).grid(row=4, column=0, columnspan=2, pady=10)
        
        # Control buttons frame
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(control_frame, text="Calculate All", command=self.calculate_bs_portfolio).pack(fill='x', pady=2)
        ttk.Button(control_frame, text="Clear All Legs", command=self.clear_bs_legs).pack(fill='x', pady=2)
        
        # === RIGHT PANEL: RESULTS ===
        
        # Individual legs results
        legs_results_frame = ttk.LabelFrame(right_panel, text="Individual Legs")
        legs_results_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        # Treeview for individual legs
        self.bs_legs_tree = ttk.Treeview(legs_results_frame, 
                                        columns=("Strike", "DTE", "Type", "Qty", "BS_Price", "Delta", "Gamma", "Vega", "Theta", "Rho"), 
                                        show="headings", height=8)
        
        # Configure columns
        columns_config = [
            ("Strike", 80), ("DTE", 60), ("Type", 60), ("Qty", 50),
            ("BS_Price", 80), ("Delta", 70), ("Gamma", 70), ("Vega", 70), ("Theta", 70), ("Rho", 70)
        ]
        
        for col, width in columns_config:
            self.bs_legs_tree.heading(col, text=col)
            self.bs_legs_tree.column(col, width=width, anchor='center')
        
        # Scrollbar for legs tree
        legs_scrollbar = ttk.Scrollbar(legs_results_frame, orient="vertical", command=self.bs_legs_tree.yview)
        self.bs_legs_tree.configure(yscrollcommand=legs_scrollbar.set)
        
        self.bs_legs_tree.pack(side='left', fill='both', expand=True)
        legs_scrollbar.pack(side='right', fill='y')
        
        # Remove leg button
        ttk.Button(legs_results_frame, text="Remove Selected Leg", command=self.remove_bs_leg).pack(pady=5)
        
        # Combined portfolio results
        portfolio_frame = ttk.LabelFrame(right_panel, text="Combined Portfolio")
        portfolio_frame.pack(fill='x', pady=(5, 0))
        
        # Portfolio metrics display
        self.bs_portfolio_text = tk.Text(portfolio_frame, height=8, wrap=tk.WORD, font=('Courier', 10))
        portfolio_scrollbar = ttk.Scrollbar(portfolio_frame, orient="vertical", command=self.bs_portfolio_text.yview)
        self.bs_portfolio_text.configure(yscrollcommand=portfolio_scrollbar.set)
        
        self.bs_portfolio_text.pack(side='left', fill='both', expand=True)
        portfolio_scrollbar.pack(side='right', fill='y')
    
    def setup_monitor_tab(self):
        # Monitoring controls
        control_frame = ttk.LabelFrame(self.monitor_frame, text="Monitoring Controls")
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Start/Stop monitoring
        self.monitor_button = ttk.Button(control_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_button.pack(pady=5)
        
        # Update interval
        ttk.Label(control_frame, text="Update Interval (minutes):").pack(pady=5)
        interval_entry = ttk.Entry(control_frame, textvariable=self.interval_var)
        interval_entry.pack(pady=5)
        
        # Alert threshold settings frame
        thresholds_frame = ttk.LabelFrame(control_frame, text="Portfolio Alert Thresholds")
        thresholds_frame.pack(fill='x', padx=5, pady=5)
        
        # P&L threshold settings
        pnl_frame = ttk.LabelFrame(thresholds_frame, text="P&L % Alerts")
        pnl_frame.pack(fill='x', padx=5, pady=2)
        
        # P&L Upper threshold
        pnl_upper_frame = ttk.Frame(pnl_frame)
        pnl_upper_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(pnl_upper_frame, text="Upper:", width=8).pack(side=tk.LEFT)
        self.pnl_upper_threshold_var = tk.StringVar(value="")
        ttk.Entry(pnl_upper_frame, textvariable=self.pnl_upper_threshold_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(pnl_upper_frame, text="Clear", width=6,
                   command=lambda: self.pnl_upper_threshold_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # P&L Lower threshold
        pnl_lower_frame = ttk.Frame(pnl_frame)
        pnl_lower_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(pnl_lower_frame, text="Lower:", width=8).pack(side=tk.LEFT)
        self.pnl_lower_threshold_var = tk.StringVar(value="")
        ttk.Entry(pnl_lower_frame, textvariable=self.pnl_lower_threshold_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(pnl_lower_frame, text="Clear", width=6,
                   command=lambda: self.pnl_lower_threshold_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # P&L Alert Remark
        pnl_remark_frame = ttk.Frame(pnl_frame)
        pnl_remark_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(pnl_remark_frame, text="Remark:").pack(side=tk.LEFT)
        self.pnl_remark_var = tk.StringVar(value="")
        ttk.Entry(pnl_remark_frame, textvariable=self.pnl_remark_var, width=30).pack(side=tk.LEFT, padx=2, fill='x', expand=True)
        
        # Delta threshold settings
        delta_frame = ttk.LabelFrame(thresholds_frame, text="Delta Alerts")
        delta_frame.pack(fill='x', padx=5, pady=2)
        
        # Delta Upper threshold
        delta_upper_frame = ttk.Frame(delta_frame)
        delta_upper_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(delta_upper_frame, text="Upper:", width=8).pack(side=tk.LEFT)
        self.delta_upper_threshold_var = tk.StringVar(value="")
        ttk.Entry(delta_upper_frame, textvariable=self.delta_upper_threshold_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(delta_upper_frame, text="Clear", width=6,
                   command=lambda: self.delta_upper_threshold_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Delta Lower threshold
        delta_lower_frame = ttk.Frame(delta_frame)
        delta_lower_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(delta_lower_frame, text="Lower:", width=8).pack(side=tk.LEFT)
        self.delta_lower_threshold_var = tk.StringVar(value="")
        ttk.Entry(delta_lower_frame, textvariable=self.delta_lower_threshold_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(delta_lower_frame, text="Clear", width=6,
                   command=lambda: self.delta_lower_threshold_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Delta Alert Remark
        delta_remark_frame = ttk.Frame(delta_frame)
        delta_remark_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(delta_remark_frame, text="Remark:").pack(side=tk.LEFT)
        self.delta_remark_var = tk.StringVar(value="")
        ttk.Entry(delta_remark_frame, textvariable=self.delta_remark_var, width=30).pack(side=tk.LEFT, padx=2, fill='x', expand=True)
        
        # Save/Load buttons
        save_load_frame = ttk.Frame(thresholds_frame)
        save_load_frame.pack(fill='x', padx=5, pady=5)
        
        button_container = ttk.Frame(save_load_frame)
        button_container.pack(expand=True)
        
        ttk.Button(button_container, text="Save All Inputs", command=self.save_all_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text="Load Saved Inputs", command=self.load_all_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text="Clear Saved Data", command=self.clear_saved_data).pack(side=tk.LEFT, padx=5)
        
        # Monitoring status
        status_frame = ttk.LabelFrame(self.monitor_frame, text="Status")
        status_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD)
        self.status_text.pack(fill='both', expand=True)
    
    def add_position(self):
        try:
            # Validate inputs
            position_type = self.position_type_var.get()
            market = self.market_var.get()
            ticker = self.ticker_var.get().strip().upper()
            quantity = int(self.quantity_var.get())
            entry_cost = float(self.entry_cost_var.get())
            
            if not ticker:
                raise ValueError("Ticker cannot be empty")
            if quantity == 0:
                raise ValueError("Quantity cannot be zero")
            if entry_cost < 0:
                raise ValueError("Entry cost cannot be negative")
            
            if position_type == "OPTION":
                # Validate option-specific inputs
                strike = float(self.strike_var.get())
                option_type = 'C' if self.option_type_var.get() == "CALL" else 'P'
                expiry_date_str = self.expiry_entry.entry.get()
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
                
                if strike <= 0:
                    raise ValueError("Strike price must be positive")
                
                # Create option code
                expiry_yymmdd = expiry_date.strftime("%y%m%d")
                strike_formatted = str(int(strike * 1000))
                option_code = f"{market}.{ticker}{expiry_yymmdd}{option_type}{strike_formatted}"
                
                # Create position object
                position = {
                    "position_type": "OPTION",
                    "option_code": option_code,
                    "quantity": quantity,
                    "entry_cost": entry_cost,
                    "leg_number": len(self.positions) + 1,
                    "user_inputs": {
                        "market": market,
                        "ticker": ticker,
                        "strike": strike,
                        "type": option_type,
                        "expiry": expiry_date.strftime("%Y-%m-%d")
                    },
                    "remark": self.position_remark_var.get(),
                    "entry_date": datetime.now().strftime("%Y-%m-%d")
                }
                
                # Add to positions list and update treeview
                self.positions.append(position)
                self.positions_tree.insert("", "end", values=(
                    position["leg_number"],
                    market,
                    ticker,
                    f"${strike:.2f}",
                    "Call" if option_type == 'C' else "Put",
                    expiry_date.strftime("%Y-%m-%d"),
                    quantity,
                    f"${entry_cost:.3f}",
                    self.position_remark_var.get()
                ))
            else:  # STOCK position
                # Get short interest rate for short positions
                short_rate = 0.0
                if quantity < 0:
                    try:
                        short_rate = float(self.short_rate_var.get())
                        if short_rate < 0:
                            raise ValueError("Short interest rate cannot be negative")
                    except ValueError as e:
                        raise ValueError("Invalid short interest rate")
                
                # Create stock position object
                position = {
                    "position_type": "STOCK",
                    "ticker": f"{market}.{ticker}",
                    "quantity": quantity,
                    "entry_cost": entry_cost,
                    "leg_number": len(self.positions) + 1,
                    "user_inputs": {
                        "market": market,
                        "ticker": ticker,
                        "short_rate": short_rate
                    },
                    "remark": self.position_remark_var.get(),
                    "entry_date": datetime.now().strftime("%Y-%m-%d")
                }
                
                # Add to positions list and update treeview
                self.positions.append(position)
                self.positions_tree.insert("", "end", values=(
                    position["leg_number"],
                    market,
                    ticker,
                    "N/A",  # No strike for stocks
                    "Stock",
                    "N/A",  # No expiry for stocks
                    quantity,
                    f"${entry_cost:.3f}",
                    self.position_remark_var.get()
                ))
            
            # Update legs listbox in spreads tab
            self.update_legs_listbox()
            
            # Clear inputs
            self.ticker_var.set("")
            self.strike_var.set("")
            self.expiry_entry.entry.delete(0, tk.END)
            self.quantity_var.set("")
            self.entry_cost_var.set("")
            self.position_remark_var.set("")
            self.short_rate_var.set("0.0")
            
            messagebox.showinfo("Success", "Position added successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def edit_position(self):
        """Edit the selected position by loading its values into the input fields."""
        selected = self.positions_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a position to edit")
            return
        
        # Get the first selected item
        item = selected[0]
        values = self.positions_tree.item(item)["values"]
        leg_number = values[0]
        
        # Find the position in our list
        position = next((pos for pos in self.positions if pos["leg_number"] == leg_number), None)
        if not position:
            messagebox.showerror("Error", "Position not found")
            return
        
        # Load values into input fields
        user_inputs = position["user_inputs"]
        self.market_var.set(user_inputs["market"])
        self.ticker_var.set(user_inputs["ticker"])
        self.strike_var.set(str(user_inputs["strike"]))
        self.option_type_var.set("CALL" if user_inputs["type"] == "C" else "PUT")
        self.quantity_var.set(str(position["quantity"]))
        self.entry_cost_var.set(str(position["entry_cost"]))
        self.position_remark_var.set(position.get("remark", ""))
        
        # Set expiry date
        try:
            expiry_date = datetime.strptime(user_inputs["expiry"], "%Y-%m-%d")
            self.expiry_entry.entry.delete(0, tk.END)
            self.expiry_entry.entry.insert(0, expiry_date.strftime("%Y-%m-%d"))
        except:
            pass
        
        # Remove the position so it can be re-added with new values
        self.positions = [p for p in self.positions if p["leg_number"] != leg_number]
        self.positions_tree.delete(item)
        
        # Renumber remaining positions
        for i, pos in enumerate(self.positions, 1):
            pos["leg_number"] = i
        
        # Refresh the treeview
        self.refresh_positions_tree()
        
        # Update legs listbox in spreads tab
        self.update_legs_listbox()
        
        messagebox.showinfo("Edit Mode", "Position loaded for editing. Modify values and click 'Add Position' to save changes.")
    
    def refresh_positions_tree(self):
        """Refresh the positions treeview with current data."""
        # Clear the treeview
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # Re-populate with current positions
        for position in self.positions:
            user_inputs = position["user_inputs"]
            position_type = position.get("position_type", "OPTION")
            if position_type == "OPTION":
                self.positions_tree.insert("", "end", values=(
                    position["leg_number"],
                    user_inputs["market"],
                    user_inputs["ticker"],
                    f"${user_inputs['strike']:.2f}",
                    "Call" if user_inputs["type"] == 'C' else "Put",
                    user_inputs["expiry"],
                    position["quantity"],
                    f"${position['entry_cost']:.3f}",
                    position.get("remark", "")
                ))
            else:  # STOCK
                self.positions_tree.insert("", "end", values=(
                    position["leg_number"],
                    user_inputs["market"],
                    user_inputs["ticker"],
                    "N/A",
                    "Stock",
                    "N/A",
                    position["quantity"],
                    f"${position['entry_cost']:.3f}",
                    position.get("remark", "")
                ))
    
    def refresh_spreads_tree(self):
        """Refresh the spreads treeview with current data."""
        # Clear the treeview
        for item in self.spreads_tree.get_children():
            self.spreads_tree.delete(item)
        
        # Re-populate with current spreads
        for spread in self.spreads:
            legs_str = ", ".join(f"Leg {num}" for num in spread['legs'])
            price_target_str = (
                f"${spread['target_price_upper']:.2f} / ${spread['target_price_lower']:.2f}" if spread['target_price_upper'] is not None and spread['target_price_lower'] is not None
                else f"${spread['target_price_upper']:.2f}" if spread['target_price_upper'] is not None
                else f"${spread['target_price_lower']:.2f}" if spread['target_price_lower'] is not None
                else "None"
            )
            delta_target_str = (
                f"{spread['target_delta_upper']:.3f} / {spread['target_delta_lower']:.3f}" if spread['target_delta_upper'] is not None and spread['target_delta_lower'] is not None
                else f"{spread['target_delta_upper']:.3f}" if spread['target_delta_upper'] is not None
                else f"{spread['target_delta_lower']:.3f}" if spread['target_delta_lower'] is not None
                else "None"
            )
            self.spreads_tree.insert("", "end", values=(
                spread['name'],
                legs_str,
                price_target_str,
                delta_target_str,
                spread.get('remark', '')
            ))
    
    def remove_position(self):
        selected = self.positions_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a position to remove")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the selected position?"):
            for item in selected:
                values = self.positions_tree.item(item)["values"]
                leg_number = values[0]
                
                # Remove from positions list
                self.positions = [p for p in self.positions if p["leg_number"] != leg_number]
                
                # Renumber remaining positions
                for i, pos in enumerate(self.positions, 1):
                    pos["leg_number"] = i
                
                # Remove from treeview
                self.positions_tree.delete(item)
            
            # Update legs listbox in spreads tab
            self.update_legs_listbox()
    
    def update_legs_listbox(self):
        self.legs_listbox.delete(0, tk.END)
        for pos in self.positions:
            position_type = pos.get("position_type", "OPTION")
            if position_type == "OPTION":
                code = pos.get("option_code", "(no code)")
                self.legs_listbox.insert(tk.END, f"Leg {pos['leg_number']}: {pos['quantity']}x {code}")
            else:  # STOCK position
                ticker = pos.get("ticker", "")
                if ticker:
                    self.legs_listbox.insert(tk.END, f"Leg {pos['leg_number']}: {pos['quantity']}x {ticker} (Stock)")
    
    def set_price_threshold(self, target_type):
        """Set price threshold based on current spread price."""
        selected_indices = self.legs_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select spread legs first")
            return
        
        try:
            # Calculate current spread price
            spread_price = 0
            for idx in selected_indices:
                pos = self.positions[idx]
                position_type = pos.get("position_type", "OPTION")
                
                if position_type == "OPTION":
                    option_code = pos.get("option_code")
                    if not option_code:
                        continue
                    ret_option, data_option_df = monitor.quote_ctx.get_market_snapshot([option_code])
                    if ret_option == monitor.RET_OK and not data_option_df.empty:
                        current_price = data_option_df.iloc[0].get('last_price', 0.0)
                        quantity = pos["quantity"]
                        spread_price += current_price * (1 if quantity > 0 else -1)
                else:  # STOCK position
                    ticker = pos.get("ticker")
                    if not ticker:
                        continue
                    try:
                        ticker_symbol = ticker.split('.')[-1]
                        stock = yf.Ticker(ticker_symbol)
                        current_price = stock.info.get('regularMarketPrice', 0.0)
                        if current_price > 0:
                            quantity = pos["quantity"]
                            spread_price += current_price * (1 if quantity > 0 else -1)
                    except:
                        continue
            
            # Update current price display
            self.current_price_var.set(f"${spread_price:.3f}/share")
            
            # Set threshold with a default buffer
            buffer_pct = 0.05  # 5% buffer
            if target_type == 'upper':
                target = spread_price * (1 + buffer_pct)
                self.upper_target_var.set(f"{target:.3f}")
            else:  # lower
                target = spread_price * (1 - buffer_pct)
                self.lower_target_var.set(f"{target:.3f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get current prices: {str(e)}")

    def set_delta_threshold(self, threshold_type):
        """Set delta threshold based on current spread delta."""
        selected_indices = self.legs_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select spread legs first")
            return
        
        try:
            # Calculate current spread delta
            spread_delta = 0
            for idx in selected_indices:
                pos = self.positions[idx]
                position_type = pos.get("position_type", "OPTION")
                
                if position_type == "OPTION":
                    option_code = pos.get("option_code")
                    if not option_code:
                        continue
                    ret_option, data_option_df = monitor.quote_ctx.get_market_snapshot([option_code])
                    if ret_option == monitor.RET_OK and not data_option_df.empty:
                        delta = data_option_df.iloc[0].get('option_delta', 0.0)
                        quantity = pos["quantity"]
                        spread_delta += delta * quantity
                else:  # STOCK position
                    # For stocks, delta is always 1.0 for long positions and -1.0 for short positions
                    quantity = pos["quantity"]
                    spread_delta += (1.0 if quantity > 0 else -1.0) * abs(quantity)
            
            # Update current delta display
            self.current_delta_var.set(f"{spread_delta:.3f}")
            
            # Set threshold with a default buffer
            buffer = 0.10  # Default buffer for delta changes
            if threshold_type == 'larger':
                self.upper_delta_target_var.set(f"{abs(spread_delta * buffer):.3f}")
                self.lower_delta_target_var.set(f"{abs(spread_delta * buffer):.3f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get current deltas: {str(e)}")

    def add_spread(self):
        try:
            # Validate inputs
            name = self.spread_name_var.get().strip()
            selected_indices = self.legs_listbox.curselection()
            print(f"DEBUG: Adding spread with legs: {[self.positions[idx] for idx in selected_indices]}")
            
            # Get target prices
            upper_price = self.upper_target_var.get().strip()
            upper_price = float(upper_price) if upper_price else None
            
            lower_price = self.lower_target_var.get().strip()
            lower_price = float(lower_price) if lower_price else None
            
            # Get delta targets
            upper_delta = self.upper_delta_target_var.get().strip()
            upper_delta = float(upper_delta) if upper_delta else None
            
            lower_delta = self.lower_delta_target_var.get().strip()
            lower_delta = float(lower_delta) if lower_delta else None
            
            if not name:
                raise ValueError("Spread name cannot be empty")
            if not selected_indices:
                raise ValueError("Please select legs for the spread")
            if upper_price is not None and lower_price is not None and upper_price <= lower_price:
                if not messagebox.askyesno("Warning", "Upper target should be higher than lower target. Continue anyway?"):
                    return
            if upper_delta is not None and lower_delta is not None and upper_delta <= lower_delta:
                if not messagebox.askyesno("Warning", "Upper delta target should be higher than lower delta target. Continue anyway?"):
                    return
            
            # Get leg numbers
            leg_numbers = [self.positions[idx]["leg_number"] for idx in selected_indices]
            
            # Create spread object
            spread = {
                'name': name,
                'legs': leg_numbers,
                'target_price_upper': upper_price,
                'target_price_lower': lower_price,
                'target_delta_upper': upper_delta,
                'target_delta_lower': lower_delta,
                "remark": self.spread_remark_var.get()
            }
            
            # Add to spreads list and update treeview
            self.spreads.append(spread)
            legs_str = ", ".join(f"Leg {num}" for num in leg_numbers)
            price_target_str = (
                f"${upper_price:.2f} / ${lower_price:.2f}" if upper_price is not None and lower_price is not None
                else f"${upper_price:.2f}" if upper_price is not None
                else f"${lower_price:.2f}" if lower_price is not None
                else "None"
            )
            delta_target_str = (
                f"{upper_delta:.2f} / {lower_delta:.2f}" if upper_delta is not None and lower_delta is not None
                else f"{upper_delta:.2f}" if upper_delta is not None
                else f"{lower_delta:.2f}" if lower_delta is not None
                else "None"
            )
            self.spreads_tree.insert("", "end", values=(
                name,
                legs_str,
                price_target_str,
                delta_target_str,
                self.spread_remark_var.get()
            ))
            
            # Save spreads configuration
            monitor.save_spreads_config(self.spreads)
            
            # Clear inputs
            self.spread_name_var.set("")
            self.legs_listbox.selection_clear(0, tk.END)
            self.upper_target_var.set("")
            self.lower_target_var.set("")
            self.upper_delta_target_var.set("")
            self.lower_delta_target_var.set("")
            self.spread_remark_var.set("")
            
            messagebox.showinfo("Success", "Spread added successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def edit_spread(self):
        """Edit the selected spread by loading its values into the input fields."""
        selected = self.spreads_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a spread to edit")
            return
        
        # Get the first selected item
        item = selected[0]
        values = self.spreads_tree.item(item)["values"]
        spread_name = values[0]
        
        # Find the spread in our list
        spread = next((s for s in self.spreads if s["name"] == spread_name), None)
        if not spread:
            messagebox.showerror("Error", "Spread not found")
            return
        
        # Load values into input fields
        self.spread_name_var.set(spread["name"])
        
        # Select the legs in the listbox
        self.legs_listbox.selection_clear(0, tk.END)
        for leg_num in spread["legs"]:
            # Find the index in the listbox (leg_num - 1 since legs are 1-indexed)
            if leg_num - 1 < self.legs_listbox.size():
                self.legs_listbox.selection_set(leg_num - 1)
        
        # Load target values
        self.upper_target_var.set(str(spread["target_price_upper"]) if spread["target_price_upper"] is not None else "")
        self.lower_target_var.set(str(spread["target_price_lower"]) if spread["target_price_lower"] is not None else "")
        self.upper_delta_target_var.set(str(spread["target_delta_upper"]) if spread["target_delta_upper"] is not None else "")
        self.lower_delta_target_var.set(str(spread["target_delta_lower"]) if spread["target_delta_lower"] is not None else "")
        self.spread_remark_var.set(spread.get("remark", ""))
        
        # Remove the spread so it can be re-added with new values
        self.spreads = [s for s in self.spreads if s["name"] != spread_name]
        self.spreads_tree.delete(item)
        
        # Save updated spreads configuration
        monitor.save_spreads_config(self.spreads)
        
        messagebox.showinfo("Edit Mode", "Spread loaded for editing. Modify values and click 'Add Spread' to save changes.")
    
    def remove_spread(self):
        selected = self.spreads_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a spread to remove")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the selected spread?"):
            for item in selected:
                values = self.spreads_tree.item(item)["values"]
                spread_name = values[0]
                
                # Remove from spreads list
                self.spreads = [s for s in self.spreads if s["name"] != spread_name]
                
                # Remove from treeview
                self.spreads_tree.delete(item)
            
            # Save updated spreads configuration
            monitor.save_spreads_config(self.spreads)
    
    def toggle_monitoring(self):
        if self.monitor_button["text"] == "Start Monitoring":
            if not self.positions:
                messagebox.showerror("Error", "No positions to monitor")
                return
            
            try:
                interval = int(self.interval_var.get())
                if interval <= 0:
                    raise ValueError("Interval must be positive")
                
                self.monitor_button["text"] = "Stop Monitoring"
                self.status_text.insert("end", "Monitoring started...\n")
                self.start_monitoring()
                
            except ValueError as e:
                messagebox.showerror("Error", str(e))
        else:
            self.monitor_button["text"] = "Start Monitoring"
            self.status_text.insert("end", "Monitoring stopped.\n")
            self.stop_monitoring()
    
    def start_monitoring(self):
        # Start the monitoring loop
        self.monitoring = True
        self.root.after(1000, self.monitor_loop)
    
    def stop_monitoring(self):
        self.monitoring = False
    
    def monitor_loop(self):
        if not self.monitoring:
            return
        
        try:
            # Update status text
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert("end", f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Get position data
            all_positions_data = []
            underlying_prices_cache = {}
            
            self.status_text.insert("end", "--- Individual Positions ---\n")
            for position in self.positions:
                print(f"DEBUG: Processing position: {position}")
                try:
                    # Determine position type (for backward compatibility)
                    position_type = position.get("position_type", "OPTION")  # Default to OPTION for existing positions
                    
                    if position_type == "OPTION":
                        option_code = position.get("option_code")
                        if not option_code:  # Handle legacy positions
                            user_inputs = position.get("user_inputs", {})
                            market = user_inputs.get("market", "US")
                            ticker = user_inputs.get("ticker", "")
                            strike = user_inputs.get("strike", 0)
                            option_type = user_inputs.get("type", "C")
                            expiry = user_inputs.get("expiry", "")
                            
                            if all([market, ticker, strike, option_type, expiry]):
                                expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
                                expiry_yymmdd = expiry_date.strftime("%y%m%d")
                                strike_formatted = str(int(strike * 1000))
                                option_code = f"{market}.{ticker}{expiry_yymmdd}{option_type}{strike_formatted}"
                                position["option_code"] = option_code  # Update the position with the option code
                        
                        if option_code:
                            self.status_text.insert("end", f"\nLeg {position['leg_number']}: {option_code}\n")
                            
                            greeks_data = monitor.get_real_option_data(option_code, underlying_prices_cache)
                            if greeks_data:
                                all_positions_data.append({
                                    "greeks_data": greeks_data,
                                    "quantity": position["quantity"],
                                    "entry_cost": position["entry_cost"]
                                })
                                
                                # Display position details
                                current_price = greeks_data['current_option_price']
                                theoretical_price = greeks_data['theoretical_price_bs']
                                quantity = position["quantity"]
                                entry_cost = position["entry_cost"]
                                
                                # Calculate P&L
                                if quantity > 0:  # Long position
                                    pnl = (current_price - entry_cost) * quantity * monitor.CONTRACT_MULTIPLIER
                                else:  # Short position
                                    pnl = (entry_cost - current_price) * abs(quantity) * monitor.CONTRACT_MULTIPLIER
                                
                                # Display market data
                                self.status_text.insert("end", f"Market Price: ${current_price:.3f}  |  BS Price: ${theoretical_price:.3f}\n")
                                self.status_text.insert("end", f"Position: {'Long' if quantity > 0 else 'Short'} {abs(quantity)}x @ ${entry_cost:.3f}\n")
                                self.status_text.insert("end", f"P&L: ${pnl:,.2f}\n")
                                
                                # Display Greeks
                                self.status_text.insert("end", f"Delta: {greeks_data['delta']:.4f}  |  Gamma: {greeks_data['gamma']:.4f}\n")
                                self.status_text.insert("end", f"Vega: {greeks_data['vega']:.4f}  |  Theta: {greeks_data['theta']:.4f}  |  Rho: {greeks_data['rho']:.4f}\n")
                                
                                if greeks_data['underlying_price'] > 0:
                                    self.status_text.insert("end", f"Underlying Price: ${greeks_data['underlying_price']:.2f}\n")
                                
                                self.status_text.insert("end", f"IV: {greeks_data['volatility']:.2%}  |  Days to Expiry: {greeks_data['days_to_expiry']}\n")
                            else:
                                self.status_text.insert("end", "Failed to get market data\n")
                        else:
                            self.status_text.insert("end", f"\nLeg {position['leg_number']}: Invalid option data\n")
                    else:  # STOCK position
                        ticker = position.get("ticker")
                        if not ticker:  # Handle legacy positions
                            user_inputs = position.get("user_inputs", {})
                            market = user_inputs.get("market", "US")
                            ticker_name = user_inputs.get("ticker", "")
                            if market and ticker_name:
                                ticker = f"{market}.{ticker_name}"
                                position["ticker"] = ticker  # Update the position with the ticker
                        
                        if ticker:
                            self.status_text.insert("end", f"\nLeg {position['leg_number']}: {ticker} (Stock)\n")
                            
                            try:
                                # Get stock data from yfinance
                                ticker_symbol = ticker.split('.')[-1]  # Get the ticker symbol without market prefix
                                stock = yf.Ticker(ticker_symbol)
                                current_price = stock.info.get('regularMarketPrice', 0.0)
                                
                                if current_price > 0:
                                    quantity = position["quantity"]
                                    entry_cost = position["entry_cost"]
                                    
                                    # Calculate P&L
                                    if quantity > 0:  # Long position
                                        pnl = (current_price - entry_cost) * quantity
                                    else:  # Short position
                                        pnl = (entry_cost - current_price) * abs(quantity)
                                        
                                        # Add short interest cost if applicable
                                        short_rate = position.get("user_inputs", {}).get("short_rate", 0.0)
                                        if short_rate > 0:
                                            days_held = (datetime.now() - datetime.strptime(position.get("entry_date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")).days
                                            short_interest_cost = abs(quantity) * entry_cost * (short_rate / 100) * (days_held / 365)
                                            pnl -= short_interest_cost
                                            self.status_text.insert("end", f"Short Interest Cost: ${short_interest_cost:,.2f}\n")
                                    
                                    # Add to positions data for portfolio summary
                                    all_positions_data.append({
                                        "greeks_data": {
                                            'current_option_price': current_price,
                                            'delta': 1.0 if quantity > 0 else -1.0,  # Stock delta is 1.0 for long, -1.0 for short
                                            'gamma': 0.0,  # Stock has no gamma
                                            'vega': 0.0,   # Stock has no vega
                                            'theta': 0.0,  # Stock has no theta
                                            'rho': 0.0     # Stock has no rho
                                        },
                                        "quantity": quantity,
                                        "entry_cost": entry_cost
                                    })
                                    
                                    # Display position details
                                    self.status_text.insert("end", f"Market Price: ${current_price:.2f}\n")
                                    self.status_text.insert("end", f"Position: {'Long' if quantity > 0 else 'Short'} {abs(quantity)} shares @ ${entry_cost:.2f}\n")
                                    self.status_text.insert("end", f"P&L: ${pnl:,.2f}\n")
                                    
                                    # Display stock-specific info
                                    if quantity < 0:  # Short position
                                        short_rate = position.get("user_inputs", {}).get("short_rate", 0.0)
                                        if short_rate > 0:
                                            self.status_text.insert("end", f"Short Interest Rate: {short_rate:.2f}%\n")
                                else:
                                    self.status_text.insert("end", "Failed to get market data from yfinance\n")
                            except Exception as e:
                                self.status_text.insert("end", f"Error getting stock data: {str(e)}\n")
                        else:
                            self.status_text.insert("end", f"\nLeg {position['leg_number']}: Invalid stock data\n")
                except Exception as e:
                    self.status_text.insert("end", f"Error processing position {position.get('leg_number', 'unknown')}: {str(e)}\n")
                    continue
            
            # Calculate and display portfolio summary
            if all_positions_data:
                print(f"DEBUG: all_positions_data = {all_positions_data}")
                combined_summary = monitor.calculate_and_display_combined_summary(all_positions_data)
                
                self.status_text.insert("end", "\n--- Portfolio Summary ---\n")
                self.status_text.insert("end", f"Total P&L: ${combined_summary['portfolio_pnl']:,.2f}\n")
                self.status_text.insert("end", f"Total Market Value: ${combined_summary['portfolio_market_value']:,.2f}\n")
                self.status_text.insert("end", f"Total BS Value: ${combined_summary['portfolio_bs_value']:,.2f}\n")
                
                self.status_text.insert("end", "\nNet Greeks (Total):\n")
                self.status_text.insert("end", f"Delta: {combined_summary['total_net_delta']:,.2f}\n")
                self.status_text.insert("end", f"Gamma: {combined_summary['total_net_gamma']:,.2f}\n")
                self.status_text.insert("end", f"Vega: {combined_summary['net_vega_per_share_equiv'] * monitor.CONTRACT_MULTIPLIER:,.2f}\n")
                self.status_text.insert("end", f"Theta: {combined_summary['net_theta_per_share_equiv'] * monitor.CONTRACT_MULTIPLIER:,.2f}\n")
                self.status_text.insert("end", f"Rho: {combined_summary['net_rho_per_share_equiv'] * monitor.CONTRACT_MULTIPLIER:,.2f}\n")
                
                # Check portfolio-level thresholds
                self.check_portfolio_thresholds(combined_summary, all_positions_data)
            
            # Monitor spreads
            if self.spreads:
                self.status_text.insert("end", "\n--- Spread Monitoring ---\n")
                for spread in self.spreads:
                    spread_metrics = self.calculate_spread_metrics(spread, self.positions)
                    if spread_metrics:
                        self.status_text.insert("end", f"\n{spread_metrics['name']}:\n")
                        price_label = "Debit" if spread_metrics['price'] > 0 else "Credit"
                        self.status_text.insert("end", f"Price: ${abs(spread_metrics['price']):.2f} {price_label} per spread\n")
                        self.status_text.insert("end", f"Delta: {spread_metrics['delta']:.3f}\n")
                        
                        # Check price targets
                        current_price = spread_metrics['price']
                        upper_target = spread.get('target_price_upper')
                        lower_target = spread.get('target_price_lower')
                        
                        if upper_target is not None and abs(current_price) >= upper_target:
                            price_label = "Debit" if current_price > 0 else "Credit"
                            alert_msg = f"Price ${abs(current_price):.2f} {price_label} per spread reached or exceeded upper target ${upper_target:.2f}"
                            if spread_metrics.get('remark'):
                                alert_msg += f"\nRemark: {spread_metrics['remark']}"
                            self.status_text.insert("end", f"ALERT: {alert_msg}\n", "alert")
                            monitor.send_notification(f"Spread Alert - {spread_metrics['name']}", alert_msg)
                        
                        if lower_target is not None and abs(current_price) <= lower_target:
                            price_label = "Debit" if current_price > 0 else "Credit"
                            alert_msg = f"Price ${abs(current_price):.2f} {price_label} per spread reached or fell below lower target ${lower_target:.2f}"
                            if spread_metrics.get('remark'):
                                alert_msg += f"\nRemark: {spread_metrics['remark']}"
                            self.status_text.insert("end", f"ALERT: {alert_msg}\n", "alert")
                            monitor.send_notification(f"Spread Alert - {spread_metrics['name']}", alert_msg)
                        
                        # Check delta targets
                        current_delta = spread_metrics['delta']
                        upper_delta = spread.get('target_delta_upper')
                        lower_delta = spread.get('target_delta_lower')
                        
                        if upper_delta is not None and current_delta >= upper_delta:
                            alert_msg = f"Delta {current_delta:.3f} reached or exceeded upper target {upper_delta:.3f}"
                            if spread_metrics.get('remark'):
                                alert_msg += f"\nRemark: {spread_metrics['remark']}"
                            self.status_text.insert("end", f"ALERT: {alert_msg}\n", "alert")
                            monitor.send_notification(f"Spread Alert - {spread_metrics['name']}", alert_msg)
                        
                        if lower_delta is not None and current_delta <= lower_delta:
                            alert_msg = f"Delta {current_delta:.3f} reached or fell below lower target {lower_delta:.3f}"
                            if spread_metrics.get('remark'):
                                alert_msg += f"\nRemark: {spread_metrics['remark']}"
                            self.status_text.insert("end", f"ALERT: {alert_msg}\n", "alert")
                            monitor.send_notification(f"Spread Alert - {spread_metrics['name']}", alert_msg)
                        
                        # Update previous values
                        if 'spreads' not in self.previous_values:
                            self.previous_values['spreads'] = {}
                        self.previous_values['spreads'][spread['name']] = {
                            'delta': current_delta
                        }
            
            # Scroll to bottom
            self.status_text.see("end")
            
            # Schedule next update
            interval_ms = int(self.interval_var.get()) * 60 * 1000
            self.root.after(interval_ms, self.monitor_loop)
            
        except Exception as e:
            self.status_text.insert("end", f"Error in monitoring loop: {str(e)}\n")
            self.stop_monitoring()
            self.monitor_button["text"] = "Start Monitoring"
            messagebox.showerror("Error", f"Monitoring stopped due to error: {str(e)}")

    def reset_spread(self):
        """Reset all spread inputs to create a new spread."""
        self.spread_name_var.set("")
        self.legs_listbox.selection_clear(0, tk.END)
        self.current_price_var.set("N/A")
        self.current_delta_var.set("N/A")
        self.upper_target_var.set("")
        self.lower_target_var.set("")
        self.upper_delta_target_var.set("")
        self.lower_delta_target_var.set("")
        self.spread_remark_var.set("")

    def get_leg_market_data(self, leg_position):
        position_type = leg_position.get("position_type", "OPTION")
        if position_type == "OPTION":
            option_code = leg_position.get("option_code")
            if not option_code:
                return None
            ret_option, data_option_df = monitor.quote_ctx.get_market_snapshot([option_code])
            if ret_option != monitor.RET_OK or data_option_df.empty:
                return None
            return {
                'label': option_code,
                'price': data_option_df.iloc[0].get('last_price', 0.0),
                'delta': data_option_df.iloc[0].get('option_delta', 0.0)
            }
        else:  # STOCK
            ticker = leg_position.get("ticker")
            if not ticker:
                return None
            ticker_symbol = ticker.split('.')[-1]
            stock = yf.Ticker(ticker_symbol)
            price = stock.info.get('regularMarketPrice', 0.0)
            if price <= 0:
                return None
            quantity = leg_position["quantity"]
            return {
                'label': ticker,
                'price': price,
                'delta': 1.0 if quantity > 0 else -1.0
            }

    def calculate_spread_metrics(self, spread, positions):
        """Calculate metrics for a specific spread."""
        spread_legs_data = []
        for leg_num in spread['legs']:
            # Find the position with matching leg number
            leg_position = next((pos for pos in positions if pos['leg_number'] == leg_num), None)
            if leg_position is None:
                return None
            try:
                market_data = self.get_leg_market_data(leg_position)
                if not market_data:
                    return None
                spread_legs_data.append({
                    'position': leg_position,
                    'market_data': market_data
                })
            except Exception as e:
                print(f"Error getting market data for leg {leg_num}: {str(e)}")
                return None
        # Calculate combined metrics
        spread_price = 0
        spread_delta = 0
        leg_details = []
        for leg_data in spread_legs_data:
            position = leg_data['position']
            market_data = leg_data['market_data']
            current_price = market_data['price']
            quantity = position['quantity']
            leg_contribution = current_price * (quantity / abs(quantity)) if quantity != 0 else 0
            delta_per_contract = market_data['delta']
            delta_contribution = delta_per_contract * (quantity / abs(quantity)) if quantity != 0 else 0
            leg_details.append({
                'code': market_data['label'],
                'price_contribution': leg_contribution,
                'delta_contribution': delta_contribution,
                'quantity': quantity,
                'market_price': current_price,
                'delta': market_data['delta']
            })
            spread_price += leg_contribution
            spread_delta += delta_contribution
        return {
            'name': spread['name'],
            'price': spread_price,
            'delta': spread_delta,
            'legs': leg_details,
            'timestamp': datetime.now().isoformat(),
            'remark': spread.get('remark', '')
        }

    def check_portfolio_thresholds(self, combined_summary, all_positions_data):
        """Check portfolio-level P&L and delta thresholds."""
        try:
            # Get current threshold values
            pnl_upper_threshold = float(self.pnl_upper_threshold_var.get()) if self.pnl_upper_threshold_var.get().strip() else None
            pnl_lower_threshold = float(self.pnl_lower_threshold_var.get()) if self.pnl_lower_threshold_var.get().strip() else None
            delta_upper_threshold = float(self.delta_upper_threshold_var.get()) if self.delta_upper_threshold_var.get().strip() else None
            delta_lower_threshold = float(self.delta_lower_threshold_var.get()) if self.delta_lower_threshold_var.get().strip() else None
            
            # Calculate initial position value for percentage P&L calculation
            initial_value = 0
            for pos_data in all_positions_data:
                initial_value += abs(pos_data['quantity']) * pos_data['entry_cost'] * monitor.CONTRACT_MULTIPLIER
            
            # Check P&L thresholds
            current_pnl = combined_summary['portfolio_pnl']
            if initial_value > 0:
                pnl_pct = (current_pnl / initial_value) * 100
                
                # Check upper P&L threshold (profit)
                if pnl_upper_threshold is not None and pnl_pct >= pnl_upper_threshold:
                    alert_msg = f"Portfolio P&L reached {pnl_pct:.1f}% (${current_pnl:,.2f})\nUpper threshold: {pnl_upper_threshold}%"
                    
                    # Add custom P&L remark
                    if self.pnl_remark_var.get().strip():
                        alert_msg += f"\nP&L Alert Remark: {self.pnl_remark_var.get()}"
                    
                    # Check for custom position remarks
                    position_remarks = []
                    for position in self.positions:
                        if position.get('remark'):
                            position_remarks.append(f"Leg {position['leg_number']}: {position['remark']}")
                    
                    if position_remarks:
                        alert_msg += f"\n\nPosition Notes:\n" + "\n".join(position_remarks)
                    
                    self.status_text.insert("end", f"\nALERT: {alert_msg}\n", "alert")
                    monitor.send_notification("Portfolio P&L Upper Alert", alert_msg)
                    
                    # Save alert data
                    alert_data = {
                        'pnl_percentage': pnl_pct,
                        'current_pnl': current_pnl,
                        'initial_value': initial_value,
                        'threshold': pnl_upper_threshold,
                        'threshold_type': 'upper',
                        'pnl_remark': self.pnl_remark_var.get(),
                        'position_remarks': position_remarks
                    }
                    monitor.save_alert_data('portfolio_pnl_upper', alert_data)
                
                # Check lower P&L threshold (loss)
                if pnl_lower_threshold is not None and pnl_pct <= pnl_lower_threshold:
                    alert_msg = f"Portfolio P&L reached {pnl_pct:.1f}% (${current_pnl:,.2f})\nLower threshold: {pnl_lower_threshold}%"
                    
                    # Add custom P&L remark
                    if self.pnl_remark_var.get().strip():
                        alert_msg += f"\nP&L Alert Remark: {self.pnl_remark_var.get()}"
                    
                    # Check for custom position remarks
                    position_remarks = []
                    for position in self.positions:
                        if position.get('remark'):
                            position_remarks.append(f"Leg {position['leg_number']}: {position['remark']}")
                    
                    if position_remarks:
                        alert_msg += f"\n\nPosition Notes:\n" + "\n".join(position_remarks)
                    
                    self.status_text.insert("end", f"\nALERT: {alert_msg}\n", "alert")
                    monitor.send_notification("Portfolio P&L Lower Alert", alert_msg)
                    
                    # Save alert data
                    alert_data = {
                        'pnl_percentage': pnl_pct,
                        'current_pnl': current_pnl,
                        'initial_value': initial_value,
                        'threshold': pnl_lower_threshold,
                        'threshold_type': 'lower',
                        'pnl_remark': self.pnl_remark_var.get(),
                        'position_remarks': position_remarks
                    }
                    monitor.save_alert_data('portfolio_pnl_lower', alert_data)
            
            # Check Delta thresholds
            current_delta = combined_summary['total_net_delta']
            
            # Check upper delta threshold
            if delta_upper_threshold is not None and current_delta >= delta_upper_threshold:
                alert_msg = f"Portfolio delta ({current_delta:,.2f}) exceeds upper threshold: {delta_upper_threshold}\nCurrent P&L: ${current_pnl:,.2f}"
                
                # Add custom delta remark
                if self.delta_remark_var.get().strip():
                    alert_msg += f"\nDelta Alert Remark: {self.delta_remark_var.get()}"
                
                # Check for custom position remarks
                position_remarks = []
                for position in self.positions:
                    if position.get('remark'):
                        position_remarks.append(f"Leg {position['leg_number']}: {position['remark']}")
                
                if position_remarks:
                    alert_msg += f"\n\nPosition Notes:\n" + "\n".join(position_remarks)
                
                self.status_text.insert("end", f"\nALERT: {alert_msg}\n", "alert")
                monitor.send_notification("Portfolio Delta Upper Alert", alert_msg)
                
                # Save alert data
                alert_data = {
                    'current_delta': current_delta,
                    'threshold': delta_upper_threshold,
                    'threshold_type': 'upper',
                    'current_pnl': current_pnl,
                    'delta_remark': self.delta_remark_var.get(),
                    'position_remarks': position_remarks
                }
                monitor.save_alert_data('portfolio_delta_upper', alert_data)
            
            # Check lower delta threshold
            if delta_lower_threshold is not None and current_delta <= delta_lower_threshold:
                alert_msg = f"Portfolio delta ({current_delta:,.2f}) below lower threshold: {delta_lower_threshold}\nCurrent P&L: ${current_pnl:,.2f}"
                
                # Add custom delta remark
                if self.delta_remark_var.get().strip():
                    alert_msg += f"\nDelta Alert Remark: {self.delta_remark_var.get()}"
                
                # Check for custom position remarks
                position_remarks = []
                for position in self.positions:
                    if position.get('remark'):
                        position_remarks.append(f"Leg {position['leg_number']}: {position['remark']}")
                
                if position_remarks:
                    alert_msg += f"\n\nPosition Notes:\n" + "\n".join(position_remarks)
                
                self.status_text.insert("end", f"\nALERT: {alert_msg}\n", "alert")
                monitor.send_notification("Portfolio Delta Lower Alert", alert_msg)
                
                # Save alert data
                alert_data = {
                    'current_delta': current_delta,
                    'threshold': delta_lower_threshold,
                    'threshold_type': 'lower',
                    'current_pnl': current_pnl,
                    'delta_remark': self.delta_remark_var.get(),
                    'position_remarks': position_remarks
                }
                monitor.save_alert_data('portfolio_delta_lower', alert_data)
            
            # Update previous values for future change detection
            self.previous_values['total_pnl'] = current_pnl
            self.previous_values['total_delta'] = current_delta
            
        except ValueError as e:
            self.status_text.insert("end", f"Error in threshold values: {e}\n")

    # === BS CALCULATOR METHODS ===
    
    def fetch_bs_market_data(self):
        """Fetch current stock price and volatility from market data."""
        ticker = self.bs_ticker_var.get().strip().upper()
        market = self.bs_market_var.get()
        
        if not ticker:
            messagebox.showwarning("Warning", "Please enter a ticker symbol")
            return
        
        try:
            # Fetch from Yahoo Finance
            print(f"Fetching market data for {ticker}...")
            stock_yf_ticker = yf.Ticker(ticker)
            stock_info = stock_yf_ticker.info
            
            # Get current price
            current_price = 0.0
            if 'currentPrice' in stock_info and stock_info['currentPrice'] is not None:
                current_price = stock_info['currentPrice']
            elif 'regularMarketPrice' in stock_info and stock_info['regularMarketPrice'] is not None:
                current_price = stock_info['regularMarketPrice']
            elif 'previousClose' in stock_info and stock_info['previousClose'] is not None:
                current_price = stock_info['previousClose']
            else:
                hist = stock_yf_ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
            
            if current_price > 0:
                self.bs_current_price_var.set(f"{current_price:.2f}")
                print(f"Fetched stock price: ${current_price:.2f}")
                messagebox.showinfo("Success", f"Market data fetched for {ticker}\nStock Price: ${current_price:.2f}")
            else:
                messagebox.showwarning("Warning", f"Could not fetch current price for {ticker}")
                return
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch market data: {str(e)}")
    
    def add_bs_leg(self):
        """Add a new option leg to the BS calculator."""
        try:
            # Validate inputs
            strike = float(self.bs_strike_var.get())
            dte = int(self.bs_dte_var.get())
            option_type = self.bs_option_type_var.get()
            quantity = int(self.bs_quantity_var.get())
            
            if strike <= 0:
                raise ValueError("Strike price must be positive")
            if dte < 0:
                raise ValueError("Days to expiration cannot be negative")
            if quantity == 0:
                raise ValueError("Quantity cannot be zero")
            
            # Create leg object
            leg = {
                'strike': strike,
                'dte': dte,
                'option_type': option_type,
                'quantity': quantity,
                'leg_id': len(self.bs_legs) + 1
            }
            
            # Add to legs list
            self.bs_legs.append(leg)
            
            # Clear input fields
            self.bs_strike_var.set("")
            self.bs_dte_var.set("")
            self.bs_quantity_var.set("1")
            
            # Recalculate and update display
            self.calculate_bs_portfolio()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def remove_bs_leg(self):
        """Remove selected leg from BS calculator."""
        selected = self.bs_legs_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leg to remove")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the selected leg?"):
            for item in selected:
                # Get the leg index from the tree item
                item_index = self.bs_legs_tree.index(item)
                if 0 <= item_index < len(self.bs_legs):
                    self.bs_legs.pop(item_index)
            
            # Renumber legs
            for i, leg in enumerate(self.bs_legs, 1):
                leg['leg_id'] = i
            
            # Recalculate and update display
            self.calculate_bs_portfolio()
    
    def clear_bs_legs(self):
        """Clear all legs from BS calculator."""
        if not self.bs_legs:
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all legs?"):
            self.bs_legs.clear()
            self.calculate_bs_portfolio()
    
    def calculate_bs_greeks(self, S, K, T, r, sigma, option_type):
        """Calculate Black-Scholes Greeks."""
        if T <= 0 or sigma <= 0:
            return {
                'price': max(0, S - K) if option_type.upper() == 'CALL' else max(0, K - S),
                'delta': 1.0 if option_type.upper() == 'CALL' and S > K else 0.0,
                'gamma': 0.0,
                'vega': 0.0,
                'theta': 0.0,
                'rho': 0.0
            }
        
        # Calculate d1 and d2
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Calculate price using existing function
        price = black_scholes_price(S, K, T, r, sigma, option_type.lower())
        
        # Calculate Greeks
        if option_type.upper() == 'CALL':
            delta = N(d1)
            rho = K * T * math.exp(-r * T) * N(d2) / 100  # Divided by 100 for 1% change
        else:  # PUT
            delta = N(d1) - 1
            rho = -K * T * math.exp(-r * T) * N(-d2) / 100  # Divided by 100 for 1% change
        
        # Common Greeks
        gamma = math.exp(-d1**2 / 2) / (S * sigma * math.sqrt(2 * math.pi * T))
        vega = S * math.exp(-d1**2 / 2) * math.sqrt(T) / (math.sqrt(2 * math.pi) * 100)  # Divided by 100 for 1% change
        theta = -(S * math.exp(-d1**2 / 2) * sigma / (2 * math.sqrt(2 * math.pi * T)) + 
                 r * K * math.exp(-r * T) * (N(d2) if option_type.upper() == 'CALL' else N(-d2))) / 365  # Per day
        
        return {
            'price': price,
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho
        }
    
    def calculate_bs_portfolio(self):
        """Calculate and display BS portfolio metrics."""
        # Clear previous results
        for item in self.bs_legs_tree.get_children():
            self.bs_legs_tree.delete(item)
        
        self.bs_portfolio_text.delete(1.0, tk.END)
        
        if not self.bs_legs:
            self.bs_portfolio_text.insert(tk.END, "No legs added yet.\n\nAdd option legs using the form on the left.")
            return
        
        try:
            # Get market parameters
            S = float(self.bs_current_price_var.get())
            sigma = float(self.bs_volatility_var.get())
            r = float(self.bs_risk_free_rate_var.get())
            
            if S <= 0:
                raise ValueError("Stock price must be positive")
            if sigma < 0:
                raise ValueError("Volatility cannot be negative")
            
            # Calculate individual legs
            total_portfolio_value = 0
            total_delta = 0
            total_gamma = 0
            total_vega = 0
            total_theta = 0
            total_rho = 0
            
            leg_results = []
            
            for leg in self.bs_legs:
                K = leg['strike']
                T = leg['dte'] / 365.0  # Convert days to years
                option_type = leg['option_type']
                quantity = leg['quantity']
                
                # Calculate Greeks
                greeks = self.calculate_bs_greeks(S, K, T, r, sigma, option_type)
                
                # Store individual leg results
                leg_result = {
                    'leg': leg,
                    'greeks': greeks,
                    'position_value': greeks['price'] * quantity * CONTRACT_MULTIPLIER
                }
                leg_results.append(leg_result)
                
                # Add to portfolio totals
                total_portfolio_value += leg_result['position_value']
                total_delta += greeks['delta'] * quantity * CONTRACT_MULTIPLIER
                total_gamma += greeks['gamma'] * quantity * CONTRACT_MULTIPLIER
                total_vega += greeks['vega'] * quantity * CONTRACT_MULTIPLIER
                total_theta += greeks['theta'] * quantity * CONTRACT_MULTIPLIER
                total_rho += greeks['rho'] * quantity * CONTRACT_MULTIPLIER
                
                # Add to tree view
                self.bs_legs_tree.insert("", "end", values=(
                    f"${K:.2f}",
                    leg['dte'],
                    option_type,
                    quantity,
                    f"${greeks['price']:.3f}",
                    f"{greeks['delta']:.4f}",
                    f"{greeks['gamma']:.4f}",
                    f"{greeks['vega']:.4f}",
                    f"{greeks['theta']:.4f}",
                    f"{greeks['rho']:.4f}"
                ))
            
            # Display portfolio summary
            portfolio_summary = f"""BLACK-SCHOLES PORTFOLIO ANALYSIS
{'='*50}

Market Parameters:
  Stock Price: ${S:.2f}
  Volatility: {sigma:.2%}
  Risk-free Rate: {r:.2%}

Portfolio Summary:
  Total Value: ${total_portfolio_value:,.2f}
  
Portfolio Greeks:
  Delta: {total_delta:,.2f} (${total_delta * S / 100:,.2f} for 1% move)
  Gamma: {total_gamma:,.2f}
  Vega: {total_vega:,.2f} (${total_vega:,.2f} for 1% vol change)
  Theta: {total_theta:,.2f} (${total_theta:,.2f} per day)
  Rho: {total_rho:,.2f} (${total_rho:,.2f} for 1% rate change)

Individual Legs:
"""
            
            for i, result in enumerate(leg_results, 1):
                leg = result['leg']
                greeks = result['greeks']
                value = result['position_value']
                
                portfolio_summary += f"""
Leg {i}: {leg['quantity']}x ${leg['strike']:.2f} {leg['option_type']} ({leg['dte']} DTE)
  Value: ${value:,.2f}
  Price: ${greeks['price']:.3f}
  Delta: {greeks['delta']:.4f}
  Gamma: {greeks['gamma']:.4f}
  Vega: {greeks['vega']:.4f}
  Theta: {greeks['theta']:.4f}
  Rho: {greeks['rho']:.4f}"""
            
            self.bs_portfolio_text.insert(tk.END, portfolio_summary)
            
            # Auto-fetch market data if enabled and ticker is set
            if self.bs_auto_fetch_var.get() and self.bs_ticker_var.get().strip():
                self.root.after(5000, self.auto_update_bs_data)  # Update after 5 seconds
            
        except ValueError as e:
            self.bs_portfolio_text.insert(tk.END, f"Error: {str(e)}\n\nPlease check your inputs.")
        except Exception as e:
            self.bs_portfolio_text.insert(tk.END, f"Calculation error: {str(e)}")
    
    def auto_update_bs_data(self):
        """Auto-update market data if enabled."""
        if self.bs_auto_fetch_var.get() and self.bs_ticker_var.get().strip():
            try:
                # Silently fetch updated price
                ticker = self.bs_ticker_var.get().strip().upper()
                stock_yf_ticker = yf.Ticker(ticker)
                stock_info = stock_yf_ticker.info
                
                current_price = 0.0
                if 'currentPrice' in stock_info and stock_info['currentPrice'] is not None:
                    current_price = stock_info['currentPrice']
                elif 'regularMarketPrice' in stock_info and stock_info['regularMarketPrice'] is not None:
                    current_price = stock_info['regularMarketPrice']
                
                if current_price > 0:
                    old_price = float(self.bs_current_price_var.get())
                    if abs(current_price - old_price) > 0.01:  # Only update if price changed significantly
                        self.bs_current_price_var.set(f"{current_price:.2f}")
                        self.calculate_bs_portfolio()  # Recalculate with new price
                
            except Exception:
                pass  # Silently fail for auto-updates

def main():
    # Use ttkbootstrap's Window for modern theming
    app = tb.Window(themename="flatly")  # Change 'flatly' to any other theme for a different look
    gui = OptionsMonitorGUI(app)
    app.mainloop()

if __name__ == "__main__":
    main()