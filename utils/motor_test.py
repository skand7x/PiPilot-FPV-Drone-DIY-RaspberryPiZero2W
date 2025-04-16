#!/usr/bin/env python3
import sys
import os
import time
import signal
import argparse
import configparser
import pigpio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MotorTester:
    def __init__(self, config_file="../config/drone_config.ini"):
        """Initialize the motor tester with configuration"""
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Initialize PiGPIO
        self.pi = pigpio.pi()
        if not self.pi.connected:
            print("Error: Could not connect to PiGPIO daemon")
            print("Please ensure pigpiod is running: sudo systemctl start pigpiod")
            sys.exit(1)
            
        # Setup motor pins (ESCs)
        self.motor_pins = [
            int(self.config['Motors']['motor1_pin']),
            int(self.config['Motors']['motor2_pin']),
            int(self.config['Motors']['motor3_pin']),
            int(self.config['Motors']['motor4_pin'])
        ]
        
        # Initialize ESCs
        self.min_pulse_width = int(self.config['Motors']['min_pulse_width'])
        self.max_pulse_width = int(self.config['Motors']['max_pulse_width'])
        self.arm_pulse_width = int(self.config['Motors']['arm_pulse_width'])
        
        # Motor labels
        self.motor_labels = ["Front Left", "Front Right", "Rear Left", "Rear Right"]
        
        # Initialize all motors to zero
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, 0)
            
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def arm_motors(self):
        """Arm all ESCs"""
        print("Arming motors...")
        
        # Set all motors to arm position
        for i, pin in enumerate(self.motor_pins):
            self.pi.set_servo_pulsewidth(pin, self.arm_pulse_width)
            print(f"  {self.motor_labels[i]} (GPIO {pin}): Armed")
            
        time.sleep(2)  # Give ESCs time to initialize
        print("Motors armed and ready for testing")
        
    def disarm_motors(self):
        """Disarm all ESCs"""
        print("Disarming motors...")
        
        # Stop all motors
        for i, pin in enumerate(self.motor_pins):
            self.pi.set_servo_pulsewidth(pin, 0)
            print(f"  {self.motor_labels[i]} (GPIO {pin}): Disarmed")
            
        print("Motors disarmed")
        
    def set_motor_speed(self, motor_index, throttle_percent):
        """Set the speed of a specific motor"""
        if motor_index < 0 or motor_index >= len(self.motor_pins):
            print(f"Error: Invalid motor index {motor_index}")
            return
            
        # Map throttle (0-100) to pulse width range
        pulse_width = self.min_pulse_width + (throttle_percent / 100.0) * (self.max_pulse_width - self.min_pulse_width)
        pulse_width = int(pulse_width)
        
        # Set motor speed
        pin = self.motor_pins[motor_index]
        self.pi.set_servo_pulsewidth(pin, pulse_width)
        
    def test_individual_motors(self, throttle=20, duration=2):
        """Test each motor individually"""
        print(f"\nTesting each motor individually at {throttle}% throttle for {duration} seconds...")
        print("CAUTION: Motors will spin! Keep clear of propellers!")
        
        # First arm all motors
        self.arm_motors()
        time.sleep(1)
        
        # Test each motor one by one
        for i in range(len(self.motor_pins)):
            print(f"\nTesting {self.motor_labels[i]} motor (GPIO {self.motor_pins[i]})...")
            self.set_motor_speed(i, throttle)
            time.sleep(duration)
            self.set_motor_speed(i, 0)
            print(f"{self.motor_labels[i]} motor test complete")
            time.sleep(1)
            
        print("\nIndividual motor tests complete")
        self.disarm_motors()
        
    def test_all_motors(self, throttle=15, duration=3):
        """Test all motors simultaneously"""
        print(f"\nTesting all motors simultaneously at {throttle}% throttle for {duration} seconds...")
        print("CAUTION: Motors will spin! Keep clear of propellers!")
        
        # First arm all motors
        self.arm_motors()
        time.sleep(1)
        
        # Run all motors
        print("Running all motors...")
        for i in range(len(self.motor_pins)):
            self.set_motor_speed(i, throttle)
            
        time.sleep(duration)
        
        # Stop all motors
        print("Stopping all motors...")
        for i in range(len(self.motor_pins)):
            self.set_motor_speed(i, 0)
            
        print("\nAll motor test complete")
        self.disarm_motors()
        
    def calibrate_escs(self):
        """Calibrate ESCs by sending min/max signals"""
        print("\n===== ESC Calibration =====")
        print("This will calibrate your ESCs. REMOVE ALL PROPELLERS before proceeding!")
        input("Press Enter to continue or Ctrl+C to abort...")
        
        print("\nDisconnect battery, press Enter when ready...")
        input()
        
        print("Setting all ESCs to maximum pulse width...")
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, self.max_pulse_width)
            
        print("\nConnect battery NOW, then wait for ESCs to beep, then press Enter...")
        input()
        
        print("Setting all ESCs to minimum pulse width...")
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, self.min_pulse_width)
            
        print("\nWait for confirmation beeps from ESCs, then press Enter...")
        input()
        
        print("Calibration complete! Stopping all signals...")
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, 0)
            
        print("ESCs are now calibrated")
        
    def interactive_test(self):
        """Interactive motor testing"""
        print("\n===== Interactive Motor Test =====")
        print("This utility allows you to test individual motors interactively.")
        print("REMOVE ALL PROPELLERS before proceeding!")
        input("Press Enter to continue or Ctrl+C to abort...")
        
        self.arm_motors()
        
        while True:
            print("\nInteractive Motor Test Menu:")
            print("  1-4: Test individual motors (1=Front Left, 2=Front Right, 3=Rear Left, 4=Rear Right)")
            print("  5: Test all motors")
            print("  0: Exit")
            
            try:
                choice = int(input("Enter choice: "))
                
                if choice == 0:
                    break
                elif 1 <= choice <= 4:
                    motor_idx = choice - 1
                    throttle = float(input(f"Enter throttle percentage (5-30) for {self.motor_labels[motor_idx]}: "))
                    throttle = max(5, min(30, throttle))  # Limit throttle for safety
                    
                    print(f"Testing {self.motor_labels[motor_idx]} at {throttle}% for 2 seconds...")
                    self.set_motor_speed(motor_idx, throttle)
                    time.sleep(2)
                    self.set_motor_speed(motor_idx, 0)
                    print("Test complete")
                    
                elif choice == 5:
                    throttle = float(input("Enter throttle percentage (5-20) for all motors: "))
                    throttle = max(5, min(20, throttle))  # Limit throttle for safety
                    duration = float(input("Enter duration in seconds (1-5): "))
                    duration = max(1, min(5, duration))  # Limit duration for safety
                    
                    print(f"Testing all motors at {throttle}% for {duration} seconds...")
                    for i in range(len(self.motor_pins)):
                        self.set_motor_speed(i, throttle)
                    time.sleep(duration)
                    for i in range(len(self.motor_pins)):
                        self.set_motor_speed(i, 0)
                    print("Test complete")
                    
                else:
                    print("Invalid choice. Please try again.")
                    
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                break
                
        print("\nExiting interactive test")
        self.disarm_motors()
        
    def cleanup(self):
        """Clean up GPIO and exit"""
        self.disarm_motors()
        self.pi.stop()
        print("Motor tester shutdown complete")
        
    def signal_handler(self, sig, frame):
        """Handle SIGINT and SIGTERM signals"""
        print("\nReceived signal to terminate")
        self.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test drone motors")
    parser.add_argument("--config", type=str, default="../config/drone_config.ini", help="Path to config file")
    parser.add_argument("--individual", action="store_true", help="Test motors individually")
    parser.add_argument("--all", action="store_true", help="Test all motors simultaneously")
    parser.add_argument("--throttle", type=float, default=15, help="Throttle percentage (5-30)")
    parser.add_argument("--duration", type=float, default=2, help="Test duration in seconds")
    parser.add_argument("--calibrate", action="store_true", help="Calibrate ESCs")
    parser.add_argument("--interactive", action="store_true", help="Interactive motor testing")
    args = parser.parse_args()
    
    # Validate throttle for safety
    throttle = max(5, min(30, args.throttle))
    
    # Initialize motor tester
    tester = MotorTester(config_file=args.config)
    
    try:
        if args.calibrate:
            tester.calibrate_escs()
        elif args.interactive:
            tester.interactive_test()
        elif args.individual:
            tester.test_individual_motors(throttle=throttle, duration=args.duration)
        elif args.all:
            tester.test_all_motors(throttle=throttle, duration=args.duration)
        else:
            # Default to interactive mode
            tester.interactive_test()
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        tester.cleanup() 