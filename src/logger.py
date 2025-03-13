import logging
from typing import Optional

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"

def setup_logger() -> logging.Logger:
    """Configure and return a logger instance."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
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
            message += f" -> Change last {interval}s: {color}{change:+.6f}%{RESET}"
        else:
            message += f" -> Change last {interval}s: {change:+.6f}%"
        if important:
            message += " 🔔 Significant Change!"
    return message

def log_price_update(logger: logging.Logger, subnet_name: str, message: str, important: bool = False) -> None:
    """Log price update with optional formatting.
    
    Args:
        logger: Logger instance
        subnet_name: Name of the subnet
        message: Price update message
        important: Whether to highlight the message
    """
    if important:
        logger.info(f"{BOLD}{subnet_name:<20} {message}{RESET}")

def log_configuration(logger: logging.Logger, config: 'Config') -> None:
    """Log monitor configuration details.
    
    Args:
        logger: Logger instance
        config: Configuration object
    """
    print("") 
    logger.info(f"{BOLD}=== TAO Price Monitor Configuration ==={RESET}")
    logger.info(f"{BOLD}Network:{RESET}      {config.network}")
    logger.info(f"{BOLD}Interval:{RESET}     {config.interval} seconds ({config.interval / 60:.1f} minutes)")
    logger.info(f"{BOLD}Alerts:{RESET}       {'Enabled' if config.alerts_on else 'Disabled'}")
    logger.info(f"{BOLD}Alert Volume:{RESET} {config.alert_volume * 100}%")
    logger.info(f"{BOLD}Monitored Subnets:{RESET}")
    for subnet in config.subnets:
        logger.info(f"  {subnet.display_name:<30} {subnet.threshold}%")
    logger.info(f"{BOLD}======================================={RESET}\n") 