import subprocess
from pathlib import Path
import logging
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages sound alerts for price changes."""
    
    def __init__(self, config: 'Config'):
        """Initialize the alert manager.
        
        Args:
            config: Configuration object containing alert settings
        """
        self.config = config
        self._sound_process: Optional[subprocess.Popen] = None
        self._sound_lock = threading.Lock()
        self._check_alert_sound_files()
    
    def _check_alert_sound_files(self) -> None:
        """Verify alert sound files exist."""
        if not Path(self.config.alert_positive).exists() or not Path(self.config.alert_negative).exists():
            logger.warning("Alert sound files not found. Sound alerts will be disabled.")
    
    def play_alert(self, is_positive: bool) -> None:
        """Play alert sound on significant price change.
        
        Args:
            is_positive: Whether the price change is positive
        """
        # Skip negative alerts if alerts_positive_only is True
        if not is_positive and self.config.alerts_positive_only:
            return
            
        if not self.config.alerts_on: 
            return
            
        # Play sound in background thread to avoid blocking
        threading.Thread(target=self._play_sound_async, args=(is_positive,), daemon=True).start()
        
    def _play_sound_async(self, is_positive: bool) -> None:
        """Play sound asynchronously to avoid blocking the main thread.
        
        Args:
            is_positive: Whether the price change is positive
        """
        try:
            with self._sound_lock:
                # Stop any currently playing sound
                if self._sound_process and self._sound_process.poll() is None:
                    self._sound_process.terminate()
                    
                sound_file = self.config.alert_positive if is_positive else self.config.alert_negative
                if Path(sound_file).exists():
                    self._sound_process = subprocess.Popen(
                        ["afplay", "-v", str(self.config.alert_volume), sound_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    print("\a")  # Fallback to standard beep
        except Exception as e:
            logger.error(f"Error playing sound alert: {e}")
            print("\a")  # Fallback to standard beep 