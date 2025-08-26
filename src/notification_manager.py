import platform
import subprocess
import threading
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .config import Config

try:
    from pync import Notifier
except ImportError:
    # Handle case where pync is not available
    Notifier = None

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
        logger.debug(f"NotificationManager initialized with alerts_positive_only={config.alerts_positive_only}")
    
    def _check_notification_support(self) -> None:
        """Check if system notifications are supported."""
        if platform.system() != 'Darwin' or Notifier is None:
            if platform.system() != 'Darwin':
                logger.warning("System notifications are only supported on macOS")
            else:
                logger.warning("pync module not available, notifications disabled")
            self.supported = False
        else:
            self.supported = True
            logger.debug("System notifications are supported on macOS")
    
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
            
        # Send notification in background thread to avoid blocking
        threading.Thread(
            target=self._send_notification_async, 
            args=(subnet_netid, subnet_name, price, change, threshold), 
            daemon=True
        ).start()
        
        # Speak subnet name using macOS text-to-speech
        if platform.system() == 'Darwin' and self.config.notification_speak:
            self._speak_subnet_name(subnet_name)
            
    def _send_notification_async(self, subnet_netid: int, subnet_name: str, price: float, change: float, threshold: float) -> None:
        """Send notification asynchronously to avoid blocking the main thread.
        
        Args:
            subnet_netid: Subnet network ID
            subnet_name: Name of the subnet
            price: Current TAO price
            change: Price change percentage
            threshold: Threshold that was exceeded
        """
        try:
            # Format the notification message with explicit negative sign
            title = f"{subnet_name}"
            # Use explicit negative sign and absolute value for clarity
            message = f"{'↓' if change < 0 else '↑'} {abs(change):.6f}%"
            message += " 🥕🐇" if change > 0 else " 👊"
            message += f"\nτ{price:.6f}"
            # Prepare notification parameters
            params = {
                'message': message,
                'title': title,
                'sound': self.config.notification_sound,  # Use config setting for sound
                # 'sender': "com.apple.Terminal",
                # 'appIcon': 'assets/icon.png',
                'group': "dTAO-monitor"
            }
            
            # Add URL opening command if configured
            if self.config.notification_url:
                url = self.config.notification_url + str(subnet_netid)
                params['open'] = url
                logger.debug(f"Adding URL to notification: {url}")
            
            logger.debug(f"Preparing to send notification with params: {params}")
            # Send notification using pync
            if Notifier is not None:
                Notifier.notify(**params)
                logger.debug(f"Successfully sent notification for {subnet_name}")
            else:
                logger.warning("Notifier not available, skipping notification")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}", exc_info=True)
            
    def _speak_subnet_name(self, subnet_name: str) -> None:
        """Speak the subnet ID and name using macOS text-to-speech.
        
        Args:
            subnet_name: Name of the subnet to speak (e.g., "62 (Ridges)")
        """
        try:
            # Format for speech: "62 Ridges" from "62 (Ridges)"
            if "(" in subnet_name and ")" in subnet_name:
                # Extract ID and name: "62 (Ridges)" -> "62 Ridges"
                parts = subnet_name.split("(")
                subnet_id = parts[0].strip()
                name_part = parts[1].split(")")[0].strip()
                speech_text = f"{subnet_id} {name_part}"
            else:
                # Fallback to original name if format doesn't match
                speech_text = subnet_name
            
            # Use macOS say command in background thread to avoid blocking
            threading.Thread(
                target=self._say_async,
                args=(speech_text,),
                daemon=True
            ).start()
            
        except Exception as e:
            logger.debug(f"Error preparing text-to-speech for {subnet_name}: {e}")
            
    def _say_async(self, text: str) -> None:
        """Execute the say command asynchronously.
        
        Args:
            text: Text to speak
        """
        try:
            # Use the built-in macOS say command
            subprocess.run(
                ["say", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5  # Prevent hanging
            )
        except Exception as e:
            logger.debug(f"Error with text-to-speech: {e}") 