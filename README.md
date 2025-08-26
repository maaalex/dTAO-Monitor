# dTAO Monitor

**dTAO Monitor** is a tool for monitoring Bittensor's subnet token prices, providing real-time insights and configurable tracking with optional alert sounds 🔔

## Features

### Price Monitoring
- Real-time monitoring of subnet token prices
- Configurable monitoring intervals
- Customizable price change thresholds
- Detailed logging with color-coded output

### Alerts
- Sound alerts for significant price changes
- System notifications (macOS only) linking to [taostats.io](https://taostats.io/) subnet pages
- Configurable alert sounds and volumes
- Optional positive-only alerts

### Price Change Alarm
- Monitors for significant price changes from initial values
- Configurable change threshold (default 3%)
- Separate sounds for positive and negative changes
- Option to only trigger alarms for negative changes
- Initial prices are recorded when the monitor starts

#### Alarm Reset Logic
- **One-time triggering**: Alarms trigger only once per significant price movement to prevent spam
- **Automatic reset**: Alarm state resets when price recovers in the opposite direction by 30% of the threshold
- **Baseline update**: When an alarm triggers, the initial price baseline is updated to the current price

## Project Structure

```
.
├── main.py              # Main entry point
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
└── src/                 # Source code package
    ├── __init__.py
    ├── config.py          # Configuration management
    ├── logger.py          # Logging utilities
    ├── alert_manager.py   # Sound alert management
    ├── price_monitor.py   # Core monitoring logic
    └── price_alarm.py     # Price drop alarm system
```

## Installation Instructions

### **1. Ensure Python 3.12 is Installed**
Bittensor requires Python **3.12** for proper functionality.
Check your Python version:
```sh
python3 --version
```
If Python 3.12 is not installed, install it via [Python.org](https://www.python.org/downloads/) or using Homebrew on macOS:
```sh
brew install python@3.12
```

### **2. Create a Virtual Environment**
Create a new virtual environment using Python 3.12:
```sh
python3.12 -m venv venv
```
Activate the virtual environment:
```sh
source venv/bin/activate
```

### **3. Install Dependencies**
Once the virtual environment is activated, install required dependencies:
```sh
pip install -r requirements.txt
```

### **4. Modify Configuration**
Customize the `config.yaml` file according to your preferences before running the monitor.

#### **Example Configuration Structure**
The configuration file allows you to specify network settings, monitoring intervals, and alert sounds.
Here is an example of the structure:

```yaml
network: "finney"
interval: 300  # seconds
threshold: 1.  # default percent change

# Alert settings
alerts_on: true
alert_positive: "sounds/yeah.mp3"
alert_negative: "sounds/wtf.mp3"
alert_volume: 0.5  # 0.0 to 1.0

# Price change alarm settings
alarm_enabled: true  # Enable price change alarm
alarm_threshold: 3.0  # Trigger alarm at 3% change
alarm_negative_only: true  # Only trigger alarms for negative changes
alarm_sound_positive: "sounds/alarm.mp3"  # Sound file for positive changes
alarm_sound_negative: "sounds/alarm.mp3"  # Sound file for negative changes
alarm_volume: 1.0  # 0.0 to 1.0

# List of subnets to monitor
subnets:
  - netuid: 13
  - netuid: 19
  - netuid: 34
  - netuid: 52
    threshold: 1.5  # subnet percent change
  - netuid: 68
    threshold: .5
```

- **`network`**: Specifies the network to connect to (e.g., "finney").
- **`interval`**: Time in seconds between monitoring checks.
- **`threshold`**: Default percent change threshold for all subnets.
- **`alerts_on`**: Enables or disables alert sounds.
- **`alert_positive` / `alert_negative`**: Audio alerts triggered based on monitoring results.
- **`alert_volume`**: Volume level for sound alerts (0.0 to 1.0).
- **`alarm_enabled`**: Enables or disables the price change alarm.
- **`alarm_threshold`**: Percentage change from initial price to trigger alarm.
- **`alarm_negative_only`**: Whether to only trigger alarms for negative changes.
- **`alarm_sound_positive` / `alarm_sound_negative`**: Sound files for positive and negative price changes.
- **`alarm_volume`**: Volume level for alarm sound (0.0 to 1.0).
- **`subnets`**: List of subnets to monitor, each identified by `netuid` and optional subnet-specific `threshold` to override default.

### **5. Run dTAO Monitor**
Start the monitor using the following command:
```sh
python main.py
```

You can also specify a custom configuration file:
```sh
python main.py --config custom_config.yaml
```

## **License**
This project is licensed under the MIT License.

## **Contributions**
Contributions and improvements are welcome! Feel free to submit a pull request or open an issue.

---
Developed with ❤️ for the Bittensor community.

