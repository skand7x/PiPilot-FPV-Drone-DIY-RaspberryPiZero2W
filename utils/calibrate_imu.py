#!/usr/bin/env python3
import sys
import os
import time
import numpy as np
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.imu import MPU6050

def calibrate_imu(samples=1000, save_file=None):
    """Calibrate the IMU by taking multiple readings and calculating offsets"""
    print("\n===== IMU Calibration Utility =====")
    print("This utility will calibrate your IMU (MPU6050) for better accuracy.")
    print("Please make sure the drone is on a flat, level surface and keep it still during calibration.")
    
    if save_file is None:
        save_file = "../config/imu_calibration.json"
    
    # Initialize IMU
    print("\nInitializing IMU... ", end="")
    try:
        imu = MPU6050()
        print("Done!")
    except Exception as e:
        print("Failed!")
        print(f"Error: {e}")
        sys.exit(1)
    
    # Start calibration
    print(f"\nStarting calibration with {samples} samples. Please keep the drone still...")
    print("3...", end="", flush=True)
    time.sleep(1)
    print("2...", end="", flush=True)
    time.sleep(1)
    print("1...", end="", flush=True)
    time.sleep(1)
    print("Calibrating...", flush=True)
    
    # Perform calibration
    try:
        accel_offsets, gyro_offsets = imu.calibrate(samples)
        
        # Print results
        print("\nCalibration complete!")
        print("\nAccelerometer offsets:")
        print(f"X: {accel_offsets[0]:.6f} g")
        print(f"Y: {accel_offsets[1]:.6f} g")
        print(f"Z: {accel_offsets[2]:.6f} g")
        
        print("\nGyroscope offsets:")
        print(f"X: {gyro_offsets[0]:.6f} °/s")
        print(f"Y: {gyro_offsets[1]:.6f} °/s")
        print(f"Z: {gyro_offsets[2]:.6f} °/s")
        
        # Save calibration
        print(f"\nSaving calibration to {save_file}... ", end="")
        imu.save_calibration(save_file)
        print("Done!")
        
        # Test calibration
        print("\nTesting calibration with a few readings:")
        for i in range(5):
            gyro_data, accel_data = imu.read_all()
            roll, pitch, yaw = imu.compute_angles(accel_data, gyro_data)
            print(f"Reading {i+1}/5:")
            print(f"Accel: X={accel_data[0]:.4f}g, Y={accel_data[1]:.4f}g, Z={accel_data[2]:.4f}g")
            print(f"Gyro: X={gyro_data[0]:.4f}°/s, Y={gyro_data[1]:.4f}°/s, Z={gyro_data[2]:.4f}°/s")
            print(f"Angles: Roll={roll:.2f}°, Pitch={pitch:.2f}°, Yaw={yaw:.2f}°")
            time.sleep(0.5)
        
        return True
        
    except Exception as e:
        print("\nCalibration failed!")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate the IMU (MPU6050)")
    parser.add_argument("--samples", type=int, default=1000, help="Number of samples to take for calibration")
    parser.add_argument("--output", type=str, default="../config/imu_calibration.json", help="Output file for calibration data")
    args = parser.parse_args()
    
    # Run calibration
    success = calibrate_imu(samples=args.samples, save_file=args.output)
    
    if success:
        print("\nCalibration completed successfully!")
        print("Your IMU is now calibrated and ready for use.")
        print("\nTips for good flight performance:")
        print("- Always calibrate the IMU when the temperature changes significantly")
        print("- Ensure the drone is level during calibration")
        print("- Re-calibrate if you notice drift during flight")
    else:
        print("\nCalibration failed. Please try again.")
        
    print("\nExiting calibration utility.")
    sys.exit(0 if success else 1) 