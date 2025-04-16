# Drone Setup Guide

## Hardware Components
- Raspberry Pi Zero 2 W
- Micro SD Card (16GB+ recommended)
- MPU6050 (Gyroscope/Accelerometer)
- 4x Brushless Motors (e.g., 2300KV Brushless Motors)
- 4x ESCs (Electronic Speed Controllers) appropriate for your motors
- Power Distribution Board
- LiPo Battery (3S or 4S, depending on your motors)
- Drone Frame
- Xbox Controller (USB connection)
- Power cables, connectors, etc.

## Hardware Assembly

### Raspberry Pi Setup
1. Install Raspberry Pi OS Lite on the microSD card
2. Enable SSH, I2C, and SPI in Raspberry Pi Configuration
3. Connect to WiFi by editing `wpa_supplicant.conf`

### Wiring Diagram
```
Raspberry Pi Zero 2 W -> MPU6050 (IMU)
- 3.3V -> VCC
- GND -> GND
- GPIO2 (SDA) -> SDA
- GPIO3 (SCL) -> SCL

Raspberry Pi Zero 2 W -> ESCs
- GPIO12 -> ESC1 Signal
- GPIO13 -> ESC2 Signal
- GPIO18 -> ESC3 Signal
- GPIO19 -> ESC4 Signal

Power Distribution:
- LiPo Battery -> Power Distribution Board
- Power Distribution Board -> ESCs
- Power Distribution Board -> BEC (5V converter) -> Raspberry Pi
```

## Software Installation

### Prerequisites
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip git
```

### Python Dependencies
```bash
sudo pip3 install RPi.GPIO pigpio numpy smbus pygame
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### Clone this Repository
```bash
git clone <url>
cd raspberry-pi-drone
```

### Controller Setup
1. Connect Xbox controller via USB to the Raspberry Pi
2. Run the test script to verify connection:
   ```bash
   python3 controller/test_controller.py
   ```

### Calibration
1. Remove propellers for safety
2. Run the calibration script:
   ```bash
   python3 utils/calibrate_imu.py
   ```
3. Follow on-screen instructions to calibrate the MPU6050

### Basic Test
1. Run the motor test (with propellers removed):
   ```bash
   python3 utils/motor_test.py
   ```

## Safety Precautions
- Always remove propellers when testing or calibrating
- Keep a safe distance when operating the drone
- Check battery voltage before flights
- Follow all local regulations regarding drone operation

## Troubleshooting
- If motors don't spin, check ESC calibration and wiring
- If the controller doesn't connect, check USB connection and permissions
- If the drone is unstable, re-calibrate the IMU
- For more issues, see the troubleshooting section in the main README 