#!/usr/bin/env python3
import time
import numpy as np
from imu import MPU6500

def main():
    # Initialize MPU6500
    imu = MPU6500()
    
    # Calibrate the IMU
    print("Starting calibration...")
    imu.calibrate(samples=1000)
    imu.save_calibration("mpu6500_calibration.json")
    
    print("\nStarting real-time angle measurements...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            # Read sensor data
            gyro_data, accel_data = imu.read_all()
            
            # Compute angles using Madgwick filter
            roll, pitch, yaw = imu.compute_angles(accel_data, gyro_data)
            
            # Get linear acceleration (without gravity)
            linear_accel = imu.get_linear_acceleration(accel_data)
            
            # Print results
            print(f"\rRoll: {roll:7.2f}°  Pitch: {pitch:7.2f}°  Yaw: {yaw:7.2f}°  "
                  f"Linear Accel: [{linear_accel[0]:6.2f}, {linear_accel[1]:6.2f}, {linear_accel[2]:6.2f}] m/s²", end="")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main() 