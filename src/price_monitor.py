import time
from typing import Dict, Optional, List
import bittensor as bt
import logging
import concurrent.futures
from datetime import datetime
import threading

from .config import Config, SubnetConfig
from .logger import format_price_message, log_price_update, log_configuration
from .alert_manager import AlertManager
from .notification_manager import NotificationManager
from .price_alarm import PriceAlarm

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
        self.last_check_time: Dict[int, Optional[datetime]] = {
            subnet.netuid: None for subnet in config.subnets
        }
        # Cache for subnet info to avoid redundant API calls
        self.subnet_info_cache: Dict[int, Optional[bt.SubnetInfo]] = {}
        self.alert_manager = AlertManager(config)
        self.notification_manager = NotificationManager(config)
        self.price_alarm = PriceAlarm(config)  # Initialize price alarm
        # Lock to prevent concurrent Subtensor API calls
        self.subtensor_lock = threading.Lock()
        self._update_subnet_info()
        self._log_configuration()
        # Persistent thread pool for parallel subnet monitoring
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(config.subnets), 10)  # Limit max workers
        )

    def _log_configuration(self) -> None:
        """Log monitor configuration details."""
        log_configuration(logger, self.config)

    def _update_subnet_info(self) -> None:
        """Update subnet information for all monitored subnets."""
        # Bittensor API isn't thread-safe, so use sequential processing here
        for subnet in self.config.subnets:
            subnet_info = self.fetch_subnet_info(subnet.netuid)
            if subnet_info:
                subnet.update_subnet_info(subnet_info)

    def fetch_subnet_info(self, netuid: int) -> Optional[bt.SubnetInfo]:
        """Fetch subnet information.
        
        Args:
            netuid: Subnet ID to fetch information for
            
        Returns:
            SubnetInfo object or None if fetch fails
        """
        try:
            # Use lock to prevent concurrent Subtensor API calls
            with self.subtensor_lock:
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
            
        # Cache subnet info to share with price alarm (avoid duplicate API calls)
        self.subnet_info_cache[subnet.netuid] = subnet_info
        
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
        self.last_check_time[subnet.netuid] = datetime.now()
        
        # Check for significant price drops using cached data
        self.price_alarm.monitor_subnet_with_cache(subnet, subnet_info)

    def monitor_all_subnets(self) -> None:
        """Monitor all subnets in parallel with optimized API usage."""
        # Clear cache before new monitoring cycle
        self.subnet_info_cache.clear()
        
        # Submit all monitoring tasks to the thread pool
        futures = [
            self.executor.submit(self.monitor_subnet, subnet)
            for subnet in self.config.subnets
        ]
        
        # Wait for all monitoring tasks to complete
        concurrent.futures.wait(futures)

    def monitor_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while True:
                start_time = time.time()
                
                # Monitor all subnets in parallel
                self.monitor_all_subnets()
                
                # Calculate remaining sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.interval - elapsed)
                
                print("…")  # new line as separator
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            # Ensure thread pool is shutdown properly
            self.executor.shutdown() 