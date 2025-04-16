#!/usr/bin/env python3
import time
import sys
import os
import numpy as np
import pigpio
import smbus
import configparser
import signal
from threading import Thread

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from controller.controller_interface import ControllerInterface
from utils.pid import PID
from utils.imu import MPU6500

class DroneController:
    def __init__(self, config_file='../config/drone_config.ini'):
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Initialize GPIO and PiGPIO
        self.pi = pigpio.pi()
        if not self.pi.connected:
            print("Error: Could not connect to PiGPIO daemon")
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
        
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, 0)
        
        # Initialize IMU (MPU6500)
        self.imu = MPU6500()
        
        # Initialize PIDs
        self.roll_pid = PID(
            float(self.config['PID']['roll_kp']),
            float(self.config['PID']['roll_ki']),
            float(self.config['PID']['roll_kd']),
            -400, 400
        )
        
        self.pitch_pid = PID(
            float(self.config['PID']['pitch_kp']),
            float(self.config['PID']['pitch_ki']),
            float(self.config['PID']['pitch_kd']),
            -400, 400
        )
        
        self.yaw_pid = PID(
            float(self.config['PID']['yaw_kp']),
            float(self.config['PID']['yaw_ki']),
            float(self.config['PID']['yaw_kd']),
            -400, 400
        )
        
        # Initialize Controller
        controller_type = self.config['Controller']['type']
        self.controller = ControllerInterface(controller_type)
        
        # Flight status
        self.armed = False
        self.flying = False
        self.throttle = 0
        self.target_roll = 0
        self.target_pitch = 0
        self.target_yaw = 0
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initialize update thread
        self.running = True
        self.update_thread = Thread(target=self.update_loop)
        self.update_thread.daemon = True
        
    def arm_motors(self):
        """Arm the ESCs"""
        print("Arming motors...")
        
        # Set all motors to arm position
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, self.arm_pulse_width)
            
        time.sleep(2)  # Give ESCs time to initialize
        self.armed = True
        print("Motors armed")
        
    def disarm_motors(self):
        """Disarm the ESCs"""
        print("Disarming motors...")
        
        # Stop all motors
        for pin in self.motor_pins:
            self.pi.set_servo_pulsewidth(pin, 0)
            
        self.armed = False
        self.flying = False
        print("Motors disarmed")
        
    def set_motor_speeds(self, throttle, roll_correction, pitch_correction, yaw_correction):
        """Set the speeds of all motors based on throttle and corrections"""
        # Map throttle (0-100) to pulse width range
        base_speed = self.min_pulse_width + (throttle / 100.0) * (self.max_pulse_width - self.min_pulse_width)
        
        # Calculate individual motor speeds
        # Motor layout:
        #   1   2
        #     X
        #   3   4
        # 1: Front Left, 2: Front Right, 3: Rear Left, 4: Rear Right
        
        m1_speed = base_speed - roll_correction + pitch_correction - yaw_correction
        m2_speed = base_speed + roll_correction + pitch_correction + yaw_correction
        m3_speed = base_speed - roll_correction - pitch_correction + yaw_correction
        m4_speed = base_speed + roll_correction - pitch_correction - yaw_correction
        
        # Ensure speeds are within limits
        speeds = [m1_speed, m2_speed, m3_speed, m4_speed]
        speeds = [max(min(s, self.max_pulse_width), self.min_pulse_width) for s in speeds]
        
        # Only set speeds if armed
        if self.armed:
            for i, pin in enumerate(self.motor_pins):
                self.pi.set_servo_pulsewidth(pin, int(speeds[i]))
    
    def update_loop(self):
        """Main control loop for drone"""
        last_time = time.time()
        
        while self.running:
            # Calculate dt
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Read IMU data
            gyro_data, accel_data = self.imu.read_all()
            roll, pitch, yaw = self.imu.compute_angles(accel_data, gyro_data)
            
            # Read controller input
            controller_data = self.controller.get_input()
            
            # Process controller commands
            if controller_data['start_pressed'] and not self.armed:
                self.arm_motors()
            elif controller_data['back_pressed'] and self.armed:
                self.disarm_motors()
                
            # Update flight parameters
            if self.armed:
                self.throttle = controller_data['left_y'] * 100  # Scale to 0-100%
                self.target_roll = controller_data['right_x'] * 30  # Scale to ±30 degrees
                self.target_pitch = controller_data['right_y'] * 30  # Scale to ±30 degrees
                self.target_yaw = controller_data['left_x'] * 180  # Scale to ±180 degrees
                
                # If throttle above threshold, consider flying
                if self.throttle > 10:
                    self.flying = True
                else:
                    self.flying = False
                    
            # Calculate PID corrections
            if self.flying:
                roll_correction = self.roll_pid.update(self.target_roll - roll, dt)
                pitch_correction = self.pitch_pid.update(self.target_pitch - pitch, dt)
                yaw_correction = self.yaw_pid.update(self.target_yaw - yaw, dt)
                
                # Set motor speeds
                self.set_motor_speeds(self.throttle, roll_correction, pitch_correction, yaw_correction)
            elif self.armed:
                # Idle motors
                self.set_motor_speeds(5, 0, 0, 0)
            
            # Sleep to maintain approximately 100Hz update rate
            time.sleep(max(0, 0.01 - (time.time() - current_time)))
    
    def start(self):
        """Start the controller"""
        print("Starting drone controller...")
        self.update_thread.start()
        
    def stop(self):
        """Stop the controller and clean up"""
        print("Stopping drone controller...")
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=2.0)
            
        self.disarm_motors()
        self.pi.stop()
        
    def signal_handler(self, sig, frame):
        """Handle SIGINT and SIGTERM signals"""
        print("\nReceived signal to terminate")
        self.stop()
        sys.exit(0)

if __name__ == "__main__":
    controller = DroneController()
    try:
        controller.start()
        # Keep main thread alive
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        controller.stop() 