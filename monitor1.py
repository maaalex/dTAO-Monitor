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
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"

@dataclass
class Config:
    """Configuration class to store runtime parameters."""
    network: str
    subnet: int
    interval: int
    threshold: float
    alert_sound: str

    @classmethod
    def from_yaml(cls, config_path: str) -> 'Config':
        """Create Config instance from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance with settings from YAML
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required config values are missing
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        required_fields = ['network', 'subnet', 'interval', 'threshold', 'alert_sound']
        missing_fields = [field for field in required_fields if field not in config_data]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        return cls(
            network=config_data['network'],
            subnet=config_data['subnet'],
            interval=config_data['interval'],
            threshold=config_data['threshold'],
            alert_sound=config_data['alert_sound']
        )

class PriceMonitor:
    def __init__(self, config: Config):
        """Initialize the TAO price monitor.
        
        Args:
            config: Configuration object containing runtime parameters
        """
        self.config = config
        self.subtensor = bt.Subtensor(network=config.network)
        self.last_price: Optional[float] = None
        self._check_alert_sound_file()
        self._log_configuration()

    def _check_alert_sound_file(self) -> None:
        """Verify alert sound file exists."""
        if not Path(self.config.alert_sound).exists():
            logger.warning(f"Alert sound file {self.config.alert_sound} not found. Sound alerts will be disabled.")

    def _log_configuration(self) -> None:
        """Log monitor configuration details."""
        subnet_info = self.fetch_subnet_details()
        print("\n") 
        logger.info(f"{BOLD}=== TAO Price Monitor Configuration ==={RESET}")
        logger.info(f"{BOLD}Network:{RESET}    {self.config.network}")
        logger.info(f"{BOLD}Subnet:{RESET}     {subnet_info}")
        logger.info(f"{BOLD}Interval:{RESET}   {self.config.interval} seconds ({self.config.interval / 60:.1f} minutes)")
        logger.info(f"{BOLD}Threshold:{RESET}  {self.config.threshold}%")
        logger.info(f"{BOLD}Alert Sound:{RESET} {self.config.alert_sound}")
        logger.info(f"{BOLD}======================================={RESET}\n")

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
            if Path(self.config.alert_sound).exists():
                subprocess.run(["afplay", self.config.alert_sound], check=True)
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
                    if abs(price_change) >= self.config.threshold:
                        self.log_price_update(current_price, price_change, important=True)
                        self.play_alert_sound()
                    else:
                        self.log_price_update(current_price, price_change)
                else:
                    self.log_price_update(current_price)
                
                self.last_price = current_price
            
            time.sleep(self.config.interval)

def parse_arguments() -> str:
    """Parse command line arguments.
    
    Returns:
        Path to configuration file
    """
    parser = argparse.ArgumentParser(description="Monitor TAO price changes")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    args = parser.parse_args()
    return args.config

def main() -> None:
    """Main entry point."""
    config_path = parse_arguments()
    
    try:
        config = Config.from_yaml(config_path)
        monitor = PriceMonitor(config)
        
        caffeinate_process = start_caffeinate()
        
        try:
            run_monitor(monitor)
        finally:
            stop_caffeinate(caffeinate_process)
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

def start_caffeinate() -> subprocess.Popen:
    """Start caffeinate process to prevent sleep."""
    return subprocess.Popen(["caffeinate", "-di"])

def stop_caffeinate(process: subprocess.Popen) -> None:
    """Stop caffeinate process."""
    if process:
        process.terminate()

def run_monitor(monitor: PriceMonitor) -> None:
    """Run the price monitor loop."""
    try:
        monitor.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
