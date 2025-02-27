import time
from datetime import datetime
import os
import subprocess
import argparse
import bittensor as bt

# Initialize the subtensor connection
sub = bt.Subtensor(network="finney")

# Store the last price
tao_last_price = None

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Fetch TAO price every N minutes")
parser.add_argument("--subnet", type=int, default=4, help="Subnet netuid (default: 4)")
parser.add_argument("--interval", type=int, default=60*5, help="Interval in seconds (default: *)")
parser.add_argument("--threshold", type=float, default=3., help="Percentage change threshold for highlighting (default: 3.0%)")

args = parser.parse_args()
interval_seconds = args.interval#  * 60

def fetch_tao_price():
    """Fetches the current TAO price from Bittensor."""
    try:
        subnet_info = sub.subnet(netuid=args.subnet)  # Adjust netuid if needed
        return subnet_info.price.tao
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def fetch_subnet_details():
    """Fetches subnet desc"""
    try:
        subnet_info = sub.subnet(netuid=args.subnet)  # Adjust netuid if needed
        return f"{subnet_info.netuid} ({subnet_info.subnet_name})"
    except Exception as e:
        print(f"Error fetching subnet details: {e}")
        return None        

def play_alert_sound():
    """Plays an alert sound on significant price change."""
    try:
        os.system("echo '\a'")  # Beep sound (may not work on all systems)
        subprocess.run(["afplay", "alert.mp3"])
    except Exception as e:
        print(f"Error playing sound: {e}")

def formated_date_time():
    return f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"

def printLog(message, level="info"):
    if level == "imp":
        print(f"\033[91m{formated_date_time()} | {fetch_subnet_details()} {message}\033[0m")
    else:
        print(f"{formated_date_time()} | \033[1m{fetch_subnet_details()}\033[0m {message}")

while True:
    tao_current_price = fetch_tao_price()
    
    if tao_current_price is not None and tao_last_price is not None:
        price_change = ((tao_current_price - tao_last_price) / tao_last_price) * 100
        printLog(f"-> TAO Price: {tao_current_price:.6f} | Change in last {args.interval}s: {price_change:.6f}%")
        # if abs(price_change) >= args.threshold:
        if price_change >= args.threshold: 
            printLog(f"| TAO Price: {tao_current_price:.6f} | Change in last {args.interval}s: {price_change:.6f}% (Significant Change!)", "imp")
            play_alert_sound()
            
    elif tao_current_price is not None:
        printLog(f"-> Initial TAO Price: {tao_current_price:.6f}")
    
    tao_last_price = tao_current_price
    
    time.sleep(interval_seconds)
