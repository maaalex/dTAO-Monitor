import platform
import subprocess
from typing import Optional
import logging
from pync import Notifier

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages system notifications for price changes."""
    
    def __init__(self, config: 'Config'):
        """Initialize the notification manager.
        
        Args:
            config: Configuration object containing notification settings
        """
        self.config = config
        self._check_notification_support()
    
    def _check_notification_support(self) -> None:
        """Check if system notifications are supported."""
        if platform.system() != 'Darwin':
            logger.warning("System notifications are only supported on macOS")
            self.supported = False
        else:
            self.supported = True
    
    def send_notification(self, subnet_netid: int, subnet_name: str, price: float, change: float, threshold: float) -> None:
        """Send a system notification for significant price changes.
        
        Args:
            subnet_name: Name of the subnet
            price: Current TAO price
            change: Price change percentage
            threshold: Threshold that was exceeded
        """
        if not self.supported:
            logger.debug("Notifications not supported on this platform")
            return
            
        # Skip negative alerts if alerts_positive_only is True
        if not change > 0 and self.config.alerts_positive_only:
            logger.debug(f"Skipping negative alert for {subnet_name} (change: {change:+.6f}%, alerts_positive_only: {self.config.alerts_positive_only})")
            return
            
        try:
            # Format the notification message
            title = f"{subnet_name}"
            message = f"{change:+.6f}% (TH: {threshold}%)\nτ{price:.6f}"
            
            # Prepare notification parameters
            params = {
                'message': message,
                'title': title,
                'sound': self.config.notification_sound,
                'group': "dTAO-monitor"
            }
            
            # Add URL opening command if configured
            if self.config.notification_url:
                url = self.config.notification_url + str(subnet_netid)
                params['open'] = url
                logger.debug(f"Adding URL to notification: {url}")
            
            logger.debug(f"Sending notification for {subnet_name}: {message}")
            # Send notification using pync
            Notifier.notify(**params)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}") 