from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import yaml
import bittensor as bt

@dataclass
class SubnetConfig:
    """Configuration for a single subnet."""
    netuid: int
    threshold: float
    _subnet_info: Optional[bt.SubnetInfo] = None

    @property
    def display_name(self) -> str:
        """Get display name for the subnet using Bittensor subnet info."""
        if self._subnet_info and self._subnet_info.subnet_name:
            return f"{self.netuid} ({self._subnet_info.subnet_name})"
        return f"Subnet {self.netuid}"

    def update_subnet_info(self, subnet_info: Optional[bt.SubnetInfo]) -> None:
        """Update subnet information.
        
        Args:
            subnet_info: New subnet information from Bittensor
        """
        self._subnet_info = subnet_info

@dataclass
class Config:
    """Configuration class to store runtime parameters."""
    network: str
    interval: int
    threshold: float  # Default threshold for all subnets
    alert_positive: str
    alert_negative: str
    subnets: List[SubnetConfig]
    alerts_on: bool = True  # Default to True for backward compatibility
    alert_volume: float = 0.5  # Default volume to 50%
    log_threshold_only: bool = False  # Only log updates that exceed threshold
    alerts_positive_only: bool = False  # Only trigger alerts for positive price changes

    @classmethod
    def from_yaml(cls, config_path: str) -> 'Config':
        """Create Config instance from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance with settings from YAML
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required config values are missing
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        required_fields = ['network', 'interval', 'threshold', 'alert_positive', 'alert_negative', 'subnets']
        missing_fields = [field for field in required_fields if field not in config_data]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        subnets = []
        for subnet_data in config_data['subnets']:
            if 'netuid' not in subnet_data:
                raise ValueError("Each subnet must have a 'netuid' field")
            subnets.append(SubnetConfig(
                netuid=subnet_data['netuid'],
                threshold=subnet_data.get('threshold', config_data['threshold'])
            ))
            
        return cls(
            network=config_data['network'],
            interval=config_data['interval'],
            threshold=config_data['threshold'],
            alert_positive=config_data['alert_positive'],
            alert_negative=config_data['alert_negative'],
            subnets=subnets,
            alerts_on=config_data.get('alerts_on', True),  # Default to True if not specified
            alert_volume=config_data.get('alert_volume', 0.5),  # Default to 50% if not specified
            log_threshold_only=config_data.get('log_threshold_only', False),  # Default to False if not specified
            alerts_positive_only=config_data.get('alerts_positive_only', False)  # Default to False if not specified
        ) 