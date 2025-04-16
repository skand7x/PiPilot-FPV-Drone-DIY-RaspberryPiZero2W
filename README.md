# Raspberry Pi Zero 2 W Drone

A DIY drone project using Raspberry Pi Zero 2 W as the flight controller.

## Components
- Raspberry Pi Zero 2 W
- 4x Brushless Motors with ESCs
- LiPo Battery
- Drone Frame
- MPU6050 (IMU for gyroscope and accelerometer)
- Xbox Controller (USB connection)

## Directory Structure
- `firmware/` - Main drone flight control code
- `controller/` - Controller interface code
- `config/` - Configuration files
- `utils/` - Utility scripts and tools

## Setup
See the setup guide in `docs/setup.md` for detailed instructions on hardware assembly and software installation.

## Usage
1. Connect the Xbox controller via USB to the Raspberry Pi
2. Power on the drone
3. Run the flight control software
4. Use the controller to fly the drone

## Safety
Always ensure propellers are removed during development and testing. Follow all local regulations regarding drone flight. 