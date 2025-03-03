#!/usr/bin/env python3

import time
from datetime import datetime
from pathlib import Path
import os
import subprocess
import argparse
from typing import Optional, Dict, List
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
class SubnetConfig:
    """Configuration for a single subnet."""
    netuid: int
    threshold: float
    _subnet_info: Optional[bt.SubnetInfo] = None

    @property
    def display_name(self) -> str:
        """Get display name for the subnet using Bittensor subnet info."""
        if self._subnet_info and self._subnet_info.subnet_name:
            return f"{self.netuid} ({self._subnet_info.subnet_name})"
        return f"Subnet {self.netuid}"

    def update_subnet_info(self, subnet_info: Optional[bt.SubnetInfo]) -> None:
        """Update subnet information.
        
        Args:
            subnet_info: New subnet information from Bittensor
        """
        self._subnet_info = subnet_info

@dataclass
class Config:
    """Configuration class to store runtime parameters."""
    network: str
    interval: int
    alert_sound: str
    subnets: List[SubnetConfig]

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
            
        required_fields = ['network', 'interval', 'alert_sound', 'subnets']
        missing_fields = [field for field in required_fields if field not in config_data]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        subnets = []
        for subnet_data in config_data['subnets']:
            if 'netuid' not in subnet_data:
                raise ValueError("Each subnet must have a 'netuid' field")
            subnets.append(SubnetConfig(
                netuid=subnet_data['netuid'],
                threshold=subnet_data.get('threshold', 3.0)
            ))
            
        return cls(
            network=config_data['network'],
            interval=config_data['interval'],
            alert_sound=config_data['alert_sound'],
            subnets=subnets
        )

class PriceMonitor:
    def __init__(self, config: Config):
        """Initialize the TAO price monitor.
        
        Args:
            config: Configuration object containing runtime parameters
        """
        self.config = config
        self.subtensor = bt.Subtensor(network=config.network)
        self.last_prices: Dict[int, Optional[float]] = {
            subnet.netuid: None for subnet in config.subnets
        }
        self._check_alert_sound_file()
        self._update_subnet_info()
        self._log_configuration()

    def _check_alert_sound_file(self) -> None:
        """Verify alert sound file exists."""
        if not Path(self.config.alert_sound).exists():
            logger.warning(f"Alert sound file {self.config.alert_sound} not found. Sound alerts will be disabled.")

    def _update_subnet_info(self) -> None:
        """Update subnet information for all monitored subnets."""
        for subnet in self.config.subnets:
            subnet_info = self.fetch_subnet_info(subnet.netuid)
            subnet.update_subnet_info(subnet_info)

    def _log_configuration(self) -> None:
        """Log monitor configuration details."""
        print("\n") 
        logger.info(f"{BOLD}=== TAO Price Monitor Configuration ==={RESET}")
        logger.info(f"{BOLD}Network:{RESET}      {self.config.network}")
        logger.info(f"{BOLD}Interval:{RESET}     {self.config.interval} seconds ({self.config.interval / 60:.1f} minutes)")
        logger.info(f"{BOLD}Alert Sound:{RESET}  {self.config.alert_sound}")
        logger.info(f"{BOLD}Monitored Subnets:{RESET}")
        for subnet in self.config.subnets:
            # logger.info(f"  {subnet.display_name} -> {subnet.threshold}%")
            logger.info(f"  {subnet.display_name}")
        logger.info(f"{BOLD}======================================={RESET}\n")

    def fetch_subnet_info(self, netuid: int) -> Optional[bt.SubnetInfo]:
        """Fetch subnet information.
        
        Args:
            netuid: Subnet ID to fetch information for
            
        Returns:
            SubnetInfo object or None if fetch fails
        """
        try:
            return self.subtensor.subnet(netuid=netuid)
        except Exception as e:
            logger.error(f"Error fetching subnet {netuid} info: {e}")
            return None

    def play_alert_sound(self) -> None:
        """Play alert sound on significant price change."""
        try:
            # Try system beep first
            # os.system("echo '\a'")
            
            # Try playing sound file if available
            if Path(self.config.alert_sound).exists():
                subprocess.run(["afplay", self.config.alert_sound], check=True)
        except Exception as e:
            logger.error(f"Error playing sound alert: {e}")

    def log_price_update(self, subnet: SubnetConfig, price: float, change: Optional[float] = None, important: bool = False) -> None:
        """Log price update with optional formatting.
        
        Args:
            subnet: Subnet configuration
            price: Current TAO price
            change: Price change percentage (optional)
            important: Whether to highlight the message (optional)
        """
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
            logger.info(f"{BOLD}{subnet.display_name} | {message}{RESET}")
        else:
            logger.info(f"{BOLD}{subnet.display_name}{RESET} -> {message}")

    def calculate_price_change(self, netuid: int, current_price: float) -> Optional[float]:
        """Calculate price change percentage.
        
        Args:
            netuid: Subnet ID
            current_price: Current TAO price
            
        Returns:
            Price change percentage or None if no previous price
        """
        last_price = self.last_prices[netuid]
        if last_price is None:
            return None
        return ((current_price - last_price) / last_price) * 100

    def monitor_subnet(self, subnet: SubnetConfig) -> None:
        """Monitor a single subnet's price.
        
        Args:
            subnet: Subnet configuration
        """
        subnet_info = self.fetch_subnet_info(subnet.netuid)
        if subnet_info is None:
            return
            
        # Update subnet info for display name
        subnet.update_subnet_info(subnet_info)
        
        current_price = subnet_info.price.tao
        price_change = self.calculate_price_change(subnet.netuid, current_price)
        
        if price_change is not None:
            if abs(price_change) >= subnet.threshold:
                self.log_price_update(subnet, current_price, price_change, important=True)
                self.play_alert_sound()
            else:
                self.log_price_update(subnet, current_price, price_change)
        else:
            self.log_price_update(subnet, current_price)
        
        self.last_prices[subnet.netuid] = current_price

    def monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            for subnet in self.config.subnets:
                self.monitor_subnet(subnet)

            print("\n")
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
