import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional
import bittensor as bt
import threading

from .config import Config, SubnetConfig
from .notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class PriceAlarm:
    """Monitors TAO prices for significant changes from initial prices."""
    
    def __init__(self, config: Config):
        """Initialize the price alarm.
        
        Args:
            config: Configuration object containing alarm settings
        """
        self.config = config
        self.subtensor = bt.Subtensor(network=config.network)
        # Store initial prices for each subnet
        self.initial_prices: Dict[int, Optional[float]] = {}
        # Lock to prevent concurrent Subtensor API calls
        self.subtensor_lock = threading.Lock()
        # Initialize notification manager
        self.notification_manager = NotificationManager(config)
        # Initialize initial prices
        self._initialize_prices()
        
    def _initialize_prices(self) -> None:
        """Initialize initial prices for all subnets."""
        if not self.config.alarm_enabled:
            return
            
        logger.info("Initializing price alarm with current subnet prices...")
        for subnet in self.config.subnets:
            subnet_info = self._fetch_subnet_info(subnet.netuid)
            if subnet_info:
                self.initial_prices[subnet.netuid] = subnet_info.price.tao
                logger.info(f"Initial price for subnet {subnet.netuid}: τ{subnet_info.price.tao:.6f}")
            else:
                self.initial_prices[subnet.netuid] = None
                logger.warning(f"Could not initialize price for subnet {subnet.netuid}")
                
    def _fetch_subnet_info(self, netuid: int) -> Optional[bt.SubnetInfo]:
        """Fetch subnet information.
        
        Args:
            netuid: Subnet ID to fetch information for
            
        Returns:
            SubnetInfo object or None if fetch fails
        """
        try:
            with self.subtensor_lock:
                return self.subtensor.subnet(netuid=netuid)
        except Exception as e:
            logger.error(f"Error fetching subnet {netuid} info: {e}")
            return None
            
    def check_price_change(self, subnet: SubnetConfig) -> None:
        """Check if current price has changed significantly from initial price.
        
        Args:
            subnet: Subnet configuration
        """
        if not self.config.alarm_enabled:
            return
            
        initial_price = self.initial_prices.get(subnet.netuid)
        if initial_price is None:
            return
            
        subnet_info = self._fetch_subnet_info(subnet.netuid)
        if subnet_info is None:
            return
            
        current_price = subnet_info.price.tao
        price_change = ((current_price - initial_price) / initial_price) * 100
        
        # Check for significant price changes
        if price_change <= -self.config.alarm_threshold:
            # Price dropped significantly
            logger.warning(f"ALARM: {subnet.display_name} price dropped {abs(price_change):.2f}% from initial price!")
            logger.warning(f"Initial: τ{initial_price:.6f} | Current: τ{current_price:.6f}")
            self._trigger_alarm(subnet, price_change, is_negative=True)
        elif not self.config.alarm_negative_only and price_change >= self.config.alarm_threshold:
            # Price increased significantly
            logger.warning(f"ALARM: {subnet.display_name} price increased {price_change:.2f}% from initial price!")
            logger.warning(f"Initial: τ{initial_price:.6f} | Current: τ{current_price:.6f}")
            self._trigger_alarm(subnet, price_change, is_negative=False)
            
    def _trigger_alarm(self, subnet: SubnetConfig, price_change: float, is_negative: bool) -> None:
        """Trigger the alarm sound and notification.
        
        Args:
            subnet: Subnet configuration
            price_change: Percentage price change
            is_negative: Whether the change is negative (price drop)
        """
        # Send system notification
        if self.config.notifications_on:
            self.notification_manager.send_notification(
                subnet_netid=subnet.netuid,
                subnet_name=subnet.display_name,
                price=self._fetch_subnet_info(subnet.netuid).price.tao,
                change=price_change,
                threshold=self.config.alarm_threshold
            )
        
        try:
            sound_file = self.config.alarm_sound_negative if is_negative else self.config.alarm_sound_positive
            if Path(sound_file).exists():
                subprocess.run(
                    ["afplay", "-v", str(self.config.alarm_volume), sound_file],
                    check=True
                )
            else:
                logger.warning(f"Alarm sound file not found: {sound_file}")
                print("\a")  # Fallback to standard beep
        except Exception as e:
            logger.error(f"Error playing alarm sound: {e}")
            
    def monitor_subnet(self, subnet: SubnetConfig) -> None:
        """Monitor a single subnet for price changes.
        
        Args:
            subnet: Subnet configuration
        """
        self.check_price_change(subnet) 