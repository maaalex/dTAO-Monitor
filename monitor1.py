#!/usr/bin/env python3

import time
from datetime import datetime
from pathlib import Path
import os
import subprocess
import argparse
from typing import Optional, Tuple
import logging
import bittensor as bt
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
NETWORK = "finney"
DEFAULT_SUBNET = 4
DEFAULT_INTERVAL = 60 * 15  # 15 minutes in seconds
DEFAULT_THRESHOLD = 3.0
ALERT_SOUND_FILE = "alert.mp3"

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"

@dataclass
class Config:
    """Configuration class to store runtime parameters."""
    subnet: int
    interval: int
    threshold: float

class PriceMonitor:
    def __init__(self, config: Config):
        """Initialize the TAO price monitor.
        
        Args:
            config: Configuration object containing runtime parameters
        """
        self.config = config
        self.subtensor = bt.Subtensor(network=NETWORK)
        self.last_price: Optional[float] = None
        self._check_alert_sound_file()

    def _check_alert_sound_file(self) -> None:
        """Verify alert sound file exists."""
        if not Path(ALERT_SOUND_FILE).exists():
            logger.warning(f"Alert sound file {ALERT_SOUND_FILE} not found. Sound alerts will be disabled.")

    def fetch_tao_price(self) -> Optional[float]:
        """Fetch the current TAO price from Bittensor.
        
        Returns:
            Current TAO price or None if fetch fails
        """
        try:
            subnet_info = self.subtensor.subnet(netuid=self.config.subnet)
            return subnet_info.price.tao
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return None

    def fetch_subnet_details(self) -> str:
        """Fetch subnet details.
        
        Returns:
            String containing subnet ID and name
        """
        try:
            subnet_info = self.subtensor.subnet(netuid=self.config.subnet)
            return f"{subnet_info.netuid} ({subnet_info.subnet_name})"
        except Exception as e:
            logger.error(f"Error fetching subnet details: {e}")
            return f"Subnet {self.config.subnet}"

    def play_alert_sound(self) -> None:
        """Play alert sound on significant price change."""
        try:
            # Try system beep first
            os.system("echo '\a'")
            
            # Try playing sound file if available
            if Path(ALERT_SOUND_FILE).exists():
                subprocess.run(["afplay", ALERT_SOUND_FILE], check=True)
        except Exception as e:
            logger.error(f"Error playing sound alert: {e}")

    def log_price_update(self, price: float, change: Optional[float] = None, important: bool = False) -> None:
        """Log price update with optional formatting.
        
        Args:
            price: Current TAO price
            change: Price change percentage (optional)
            important: Whether to highlight the message (optional)
        """
        subnet_info = self.fetch_subnet_details()
        message = f"TAO Price: {price:.6f}"
        if change is not None:
            if change != 0:
                color = GREEN if change > 0 else RED
                message += f" | Change in last {self.config.interval}s: {color}{change:+.6f}%{RESET}"
            else:
                message += f" | Change in last {self.config.interval}s: {change:+.6f}%"
            if important:
                message += " (Significant Change!)"

        if important:
            logger.info(f"{BOLD}{subnet_info} | {message}{RESET}")
        else:
            logger.info(f"{BOLD}{subnet_info}{RESET} -> {message}")

    def calculate_price_change(self, current_price: float) -> Optional[float]:
        """Calculate price change percentage.
        
        Args:
            current_price: Current TAO price
            
        Returns:
            Price change percentage or None if no previous price
        """
        if self.last_price is None:
            return None
        return ((current_price - self.last_price) / self.last_price) * 100

    def monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            current_price = self.fetch_tao_price()
            
            if current_price is not None:
                price_change = self.calculate_price_change(current_price)
                
                if price_change is not None:
                    self.log_price_update(current_price, price_change)
                    if abs(price_change) >= self.config.threshold:
                        self.log_price_update(current_price, price_change, important=True)
                        self.play_alert_sound()
                else:
                    self.log_price_update(current_price)
                
                self.last_price = current_price
            
            time.sleep(self.config.interval)

def parse_arguments() -> Config:
    """Parse command line arguments.
    
    Returns:
        Config object containing runtime parameters
    """
    parser = argparse.ArgumentParser(description="Monitor TAO price changes")
    parser.add_argument(
        "--subnet",
        type=int,
        default=DEFAULT_SUBNET,
        help=f"Subnet netuid (default: {DEFAULT_SUBNET})"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Interval in seconds (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Percentage change threshold for highlighting (default: {DEFAULT_THRESHOLD}%)"
    )
    
    args = parser.parse_args()
    return Config(
        subnet=args.subnet,
        interval=args.interval,
        threshold=args.threshold
    )

def main() -> None:
    """Main entry point."""
    config = parse_arguments()
    monitor = PriceMonitor(config)
    
    try:
        monitor.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
