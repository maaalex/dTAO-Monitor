import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages sound alerts for price changes."""
    
    def __init__(self, config: 'Config'):
        """Initialize the alert manager.
        
        Args:
            config: Configuration object containing alert settings
        """
        self.config = config
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
        if not self.config.alerts_on:
            return
            
        try:
            sound_file = self.config.alert_positive if is_positive else self.config.alert_negative
            if Path(sound_file).exists():
                subprocess.run(["afplay", "-v", str(self.config.alert_volume), sound_file], check=True)
        except Exception as e:
            logger.error(f"Error playing sound alert: {e}") 