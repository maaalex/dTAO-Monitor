import argparse
import logging
import os
import signal
import sys
import time
from typing import Optional

from src.config import Config
from src.logger import setup_logger
from src.price_monitor import PriceMonitor

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Monitor TAO prices for specified subnets.')
    parser.add_argument('--config', type=str, default='config.yaml',
                      help='Path to configuration file')
    return parser.parse_args()

def start_caffeinate() -> Optional[int]:
    """Start caffeinate process to prevent system sleep.
    
    Returns:
        Process ID of caffeinate or None if failed
    """
    try:
        import subprocess
        process = subprocess.Popen(['caffeinate', '-i'])
        return process.pid
    except Exception as e:
        logging.error(f"Failed to start caffeinate: {e}")
        return None

def stop_caffeinate(pid: Optional[int]) -> None:
    """Stop caffeinate process.
    
    Args:
        pid: Process ID of caffeinate to stop
    """
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logging.error(f"Failed to stop caffeinate: {e}")

def main() -> None:
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    setup_logger()
    logger = logging.getLogger(__name__)
    
    # Initialize caffeinate process
    caffeinate_pid = None
    
    try:
        # Load configuration
        config = Config.from_yaml(args.config)
        
        # Start caffeinate to prevent system sleep
        caffeinate_pid = start_caffeinate()
        
        # Create and start monitor
        monitor = PriceMonitor(config)
        monitor.monitor_loop()
            
    except KeyboardInterrupt:
        logger.info("Stopping TAO price monitor")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Always stop caffeinate, even if there's an error
        stop_caffeinate(caffeinate_pid)

if __name__ == '__main__':
    main() 