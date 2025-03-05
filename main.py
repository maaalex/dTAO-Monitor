import argparse
import subprocess
import logging

from src.config import Config
from src.price_monitor import PriceMonitor
from src.logger import setup_logger

logger = setup_logger()

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
        logger.warning("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

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

if __name__ == "__main__":
    main() 