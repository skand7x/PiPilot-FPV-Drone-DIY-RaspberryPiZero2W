#!/usr/bin/env python3
import os
import sys
import time
import signal
import argparse
import configparser

from firmware.drone_controller import DroneController

def setup_environment():
    """Setup the environment for the drone controller"""
    print("Setting up drone environment...")
    
    # Check if pigpiod is running
    if os.system("pgrep pigpiod > /dev/null") != 0:
        print("Starting pigpiod daemon...")
        os.system("sudo pigpiod")
        time.sleep(1)  # Wait for pigpiod to start
    
    # Ensure config directory exists
    os.makedirs("config", exist_ok=True)

def main():
    """Main function to start the drone controller"""
    parser = argparse.ArgumentParser(description="Raspberry Pi Drone Controller")
    parser.add_argument("--config", type=str, default="config/drone_config.ini", help="Path to configuration file")
    parser.add_argument("--controller", type=str, choices=["xbox", "mobile"], default=None, help="Override controller type")
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)
    
    # Override controller type if specified
    if args.controller:
        config = configparser.ConfigParser()
        config.read(args.config)
        config['Controller']['type'] = args.controller
        with open(args.config, 'w') as configfile:
            config.write(configfile)
        print(f"Controller type set to: {args.controller}")
    
    print("\n===== Raspberry Pi Drone Controller =====")
    print("Starting drone controller...")
    
    # Initialize controller
    controller = DroneController(config_file=args.config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\nReceived signal to terminate")
        controller.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start controller
    try:
        controller.start()
        print("\nDrone controller is running. Press Ctrl+C to exit.")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        controller.stop()

if __name__ == "__main__":
    main() 