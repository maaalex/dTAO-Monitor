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
    parser.add_argument('--config', type=str, default='config/config.yaml',
                      help='Path to configuration file')
    return parser.parse_args()

def start_caffeinate() -> Optional[int]:
    """Start caffeinate process to prevent system sleep.
    
    Returns:
        Process ID of caffeinate or None if failed
    """
    try:
        import subprocess
        # Use -d to prevent display sleep and -i to prevent idle sleep
        process = subprocess.Popen(['caffeinate', '-id'])
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
            # Wait a bit to ensure the process is terminated
            time.sleep(0.1)
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
    
    def cleanup(signum=None, frame=None):
        """Cleanup function to ensure caffeinate is stopped."""
        nonlocal caffeinate_pid
        if caffeinate_pid:
            # logger.info("Stopping caffeinate process...")
            stop_caffeinate(caffeinate_pid)
            caffeinate_pid = None
        # Exit the script after cleanup
        sys.exit(0)
    
    try:
        # Load configuration
        config = Config.from_yaml(args.config)
        
        # Start caffeinate to prevent system sleep
        caffeinate_pid = start_caffeinate()
        # if caffeinate_pid:
            # logger.info("Started caffeinate to prevent system sleep")
        
        # Create and start monitor
        monitor = PriceMonitor(config)
        monitor.monitor_loop()
            
    except KeyboardInterrupt:
        logger.info("Stopping TAO price monitor")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        cleanup()
        sys.exit(1)
    finally:
        # Always stop caffeinate, even if there's an error
        cleanup()

if __name__ == '__main__':
    main() 