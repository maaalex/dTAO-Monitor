import time
from typing import Dict, Optional
import bittensor as bt
import logging

from .config import Config, SubnetConfig
from .logger import format_price_message, log_price_update, log_configuration
from .alert_manager import AlertManager
from .notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitors TAO prices for specified subnets."""
    
    def __init__(self, config: Config):
        """Initialize the TAO price monitor.
        
        Args:
            config: Configuration object containing runtime parameters
        """
        self.config = config
        self.subtensor = bt.Subtensor(network=config.network)
        logger.info(f"Connected to Bittensor network: {config.network}")
        self.last_prices: Dict[int, Optional[float]] = {
            subnet.netuid: None for subnet in config.subnets
        }
        self.alert_manager = AlertManager(config)
        self.notification_manager = NotificationManager(config)
        self._update_subnet_info()
        self._log_configuration()

    def _log_configuration(self) -> None:
        """Log monitor configuration details."""
        log_configuration(logger, self.config)

    def _update_subnet_info(self) -> None:
        """Update subnet information for all monitored subnets."""
        for subnet in self.config.subnets:
            subnet_info = self.fetch_subnet_info(subnet.netuid)
            subnet.update_subnet_info(subnet_info)

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
                message = format_price_message(current_price, price_change, self.config.interval, important=True)
                log_price_update(logger, subnet.display_name, message, important=True)
                
                # Play sound alert
                self.alert_manager.play_alert(price_change > 0)
                
                # Send system notification
                if self.config.notifications_on:
                    logger.debug(f"Attempting to send notification for {subnet.display_name}: change={price_change:+.6f}%, threshold={subnet.threshold}%, alerts_positive_only={self.config.alerts_positive_only}")
                    self.notification_manager.send_notification(
                        subnet_netid=subnet.netuid,
                        subnet_name=subnet.display_name,
                        price=current_price,
                        change=price_change,
                        threshold=subnet.threshold
                    )
            else:
                # Only log non-threshold changes if log_threshold_only is False
                if not self.config.log_threshold_only:
                    message = format_price_message(current_price, price_change, self.config.interval)
                    log_price_update(logger, subnet.display_name, message)
        else:
            # Always log initial price
            message = format_price_message(current_price)
            log_price_update(logger, subnet.display_name, message)
        
        self.last_prices[subnet.netuid] = current_price

    def monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            for subnet in self.config.subnets:
                self.monitor_subnet(subnet)

            print("…") # new line as separator
            time.sleep(self.config.interval) 