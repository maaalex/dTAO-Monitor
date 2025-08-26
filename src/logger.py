import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"

class CustomFormatter(logging.Formatter):
    """Custom formatter to remove 'INFO -' from normal messages but keep it for warnings/errors."""
    
    def format(self, record):
        if record.levelno == logging.INFO:
            # For INFO messages, only show timestamp and message
            return f"{self.formatTime(record, self.datefmt)} - {record.getMessage()}"
        else:
            # For WARNING, ERROR, etc., include the level name
            return f"{self.formatTime(record, self.datefmt)} - {record.levelname} - {record.getMessage()}"

def setup_logger() -> logging.Logger:
    """Configure and return a logger instance."""
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    formatter = CustomFormatter(datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

def format_price_message(price: float, change: Optional[float] = None, interval: int = 0, important: bool = False) -> str:
    """Format price update message with optional change percentage.
    
    Args:
        price: Current TAO price
        change: Price change percentage (optional)
        interval: Monitoring interval in seconds
        important: Whether to highlight the message
        
    Returns:
        Formatted message string
    """
    message = f"τ{price:.6f}"
    if change is not None:
        if change != 0:
            color = GREEN if change > 0 else RED
            message += f" | {color}{change:+.6f}%{RESET} ({interval}s)"
            if important:
                message += " 🥕🐇" if change > 0 else " 👊"
        else:
            message += f" | {change:+.6f}% ({interval}s)"
    return message

def log_price_update(logger: logging.Logger, subnet_name: str, message: str, important: bool = False) -> None:
    """Log price update with optional formatting.
    
    Args:
        logger: Logger instance
        subnet_name: Name of the subnet
        message: Price update message
        important: Whether to highlight the message
    """
    truncated_name = subnet_name[:20]
    if important:
        logger.info(f"{BOLD}{truncated_name:<20} {message}{RESET}")
    else:
        logger.info(f"{truncated_name:<20} {message}")

def log_configuration(logger: logging.Logger, config: 'Config') -> None:
    """Log monitor configuration details.
    
    Args:
        logger: Logger instance
        config: Configuration object
    """
    print("") 
    logger.info(f"{BOLD}=== TAO Price Monitor Configuration ==={RESET}")
    logger.info(f"{BOLD}Network:{RESET}                 {config.network}")
    logger.info(f"{BOLD}Interval:{RESET}                {config.interval}s ({config.interval / 60:.1f} minutes)")
    logger.info(f"{BOLD}Alerts:{RESET}                  {'Yes' if config.alerts_on else 'No'}")
    logger.info(f"{BOLD}Alert Volume:{RESET}            {config.alert_volume * 100}%")
    logger.info(f"{BOLD}Log Threshold Only:{RESET}      {'Yes' if config.log_threshold_only else 'No'}")
    logger.info(f"{BOLD}Positive Alerts Only:{RESET}    {'Yes' if config.alerts_positive_only else 'No'}")
    logger.info(f"{BOLD}System Notifications:{RESET}    {'Yes' if config.notifications_on else 'No'}")
    logger.info(f"{BOLD}Notification Sound:{RESET}      {'Yes' if config.notification_sound else 'No'}")
    logger.info(f"{BOLD}Text-to-Speech:{RESET}          {'Yes' if config.notification_speak else 'No'}")
    if config.notification_url:
        logger.info(f"{BOLD}Notification URL:{RESET}        {config.notification_url}")
    # Alarm settings
    logger.info(f"{BOLD}Price Change Alarm:{RESET}      {'Yes' if config.alarm_enabled else 'No'}")
    if config.alarm_enabled:
        logger.info(f"{BOLD}Alarm Threshold:{RESET}         {config.alarm_threshold}%")
        logger.info(f"{BOLD}Alarm Sound:{RESET}             {config.alarm_sound_positive} (positive) / {config.alarm_sound_negative} (negative)")
        logger.info(f"{BOLD}Alarm Volume:{RESET}            {config.alarm_volume * 100}%")
    logger.info(f"{BOLD}Monitored Subnets:{RESET}")
    for subnet in config.subnets:
        logger.info(f"  {subnet.display_name:<30} {subnet.threshold}%")
    logger.info(f"{BOLD}======================================={RESET}\n") 