#!/usr/bin/env python3
import smbus
import time
import math
import numpy as np
import json
import os

class MPU6050:
    # MPU6050 Registers
    PWR_MGMT_1 = 0x6B
    SMPLRT_DIV = 0x19
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    INT_ENABLE = 0x38
    ACCEL_XOUT_H = 0x3B
    ACCEL_YOUT_H = 0x3D
    ACCEL_ZOUT_H = 0x3F
    GYRO_XOUT_H = 0x43
    GYRO_YOUT_H = 0x45
    GYRO_ZOUT_H = 0x47
    
    def __init__(self, address=0x68, bus=1, calibration_file=None):
        self.address = address
        self.bus = smbus.SMBus(bus)
        
        # Wake up the MPU6050
        self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0)
        
        # Configure gyroscope range (±250°/s)
        self.bus.write_byte_data(self.address, self.GYRO_CONFIG, 0)
        
        # Configure accelerometer range (±2g)
        self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0)
        
        # Set sample rate to 100Hz
        self.bus.write_byte_data(self.address, self.SMPLRT_DIV, 9)
        
        # Load calibration data if available
        self.accel_offsets = np.array([0.0, 0.0, 0.0])
        self.gyro_offsets = np.array([0.0, 0.0, 0.0])
        
        if calibration_file:
            self.load_calibration(calibration_file)
        
        # Initialize complementary filter variables
        self.last_time = time.time()
        self.last_angles = np.array([0.0, 0.0, 0.0])  # [roll, pitch, yaw]
        self.complementary_alpha = 0.98  # Weight for gyro vs accelerometer
        
    def read_i2c_word(self, register):
        """Read a word from I2C device"""
        high = self.bus.read_byte_data(self.address, register)
        low = self.bus.read_byte_data(self.address, register + 1)
        value = (high << 8) + low
        
        if value >= 0x8000:
            value = -((65535 - value) + 1)
            
        return value
        
    def read_accel_data(self):
        """Read accelerometer data and apply calibration"""
        x = self.read_i2c_word(self.ACCEL_XOUT_H)
        y = self.read_i2c_word(self.ACCEL_YOUT_H)
        z = self.read_i2c_word(self.ACCEL_ZOUT_H)
        
        # Convert to g's (1g = 16384 according to datasheet)
        accel_scale = 16384.0
        x = x / accel_scale
        y = y / accel_scale
        z = z / accel_scale
        
        # Apply calibration offsets
        x -= self.accel_offsets[0]
        y -= self.accel_offsets[1]
        z -= self.accel_offsets[2]
        
        return np.array([x, y, z])
        
    def read_gyro_data(self):
        """Read gyroscope data and apply calibration"""
        x = self.read_i2c_word(self.GYRO_XOUT_H)
        y = self.read_i2c_word(self.GYRO_YOUT_H)
        z = self.read_i2c_word(self.GYRO_ZOUT_H)
        
        # Convert to degrees per second (1 dps = 131.0 according to datasheet)
        gyro_scale = 131.0
        x = x / gyro_scale
        y = y / gyro_scale
        z = z / gyro_scale
        
        # Apply calibration offsets
        x -= self.gyro_offsets[0]
        y -= self.gyro_offsets[1]
        z -= self.gyro_offsets[2]
        
        return np.array([x, y, z])
        
    def read_all(self):
        """Read both gyro and accelerometer data at once"""
        gyro_data = self.read_gyro_data()
        accel_data = self.read_accel_data()
        return gyro_data, accel_data
        
    def compute_angles_from_accel(self, accel_data):
        """Calculate roll and pitch from accelerometer data"""
        x, y, z = accel_data
        
        # Calculate roll and pitch in radians
        roll = math.atan2(y, z)
        pitch = math.atan2(-x, math.sqrt(y*y + z*z))
        
        # Convert to degrees
        roll = math.degrees(roll)
        pitch = math.degrees(pitch)
        
        return roll, pitch
        
    def compute_angles(self, accel_data, gyro_data):
        """Compute roll, pitch, and yaw using complementary filter"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Get roll and pitch from accelerometer
        accel_roll, accel_pitch = self.compute_angles_from_accel(accel_data)
        
        # Integrate gyro rates to get angles
        gyro_roll = self.last_angles[0] + gyro_data[0] * dt
        gyro_pitch = self.last_angles[1] + gyro_data[1] * dt
        gyro_yaw = self.last_angles[2] + gyro_data[2] * dt
        
        # Apply complementary filter
        roll = self.complementary_alpha * gyro_roll + (1 - self.complementary_alpha) * accel_roll
        pitch = self.complementary_alpha * gyro_pitch + (1 - self.complementary_alpha) * accel_pitch
        yaw = gyro_yaw  # Yaw can't be corrected with accelerometer
        
        # Update last angles
        self.last_angles = np.array([roll, pitch, yaw])
        
        return roll, pitch, yaw
        
    def calibrate(self, samples=1000):
        """Calibrate the IMU by taking multiple readings and averaging"""
        print("Calibrating IMU. Keep the device still...")
        
        accel_readings = []
        gyro_readings = []
        
        # Take readings
        for _ in range(samples):
            gyro_data, accel_data = self.read_all()
            accel_readings.append(accel_data)
            gyro_readings.append(gyro_data)
            time.sleep(0.005)  # 5ms delay
            
        # Convert to numpy arrays
        accel_readings = np.array(accel_readings)
        gyro_readings = np.array(gyro_readings)
        
        # Calculate mean offsets
        accel_offsets = np.mean(accel_readings, axis=0)
        gyro_offsets = np.mean(gyro_readings, axis=0)
        
        # Z-axis of accelerometer should read 1g when the device is flat
        accel_offsets[2] = accel_offsets[2] - 1.0
        
        # Set offsets
        self.accel_offsets = accel_offsets
        self.gyro_offsets = gyro_offsets
        
        print("Calibration complete!")
        print(f"Accelerometer offsets: {accel_offsets}")
        print(f"Gyroscope offsets: {gyro_offsets}")
        
        return accel_offsets, gyro_offsets
        
    def save_calibration(self, filename="../config/imu_calibration.json"):
        """Save calibration data to a file"""
        calibration_data = {
            "accel_offsets": self.accel_offsets.tolist(),
            "gyro_offsets": self.gyro_offsets.tolist()
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=4)
            
        print(f"Calibration saved to {filename}")
        
    def load_calibration(self, filename="../config/imu_calibration.json"):
        """Load calibration data from a file"""
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
                
            self.accel_offsets = np.array(calibration_data["accel_offsets"])
            self.gyro_offsets = np.array(calibration_data["gyro_offsets"])
            
            print(f"Loaded calibration from {filename}")
            return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False

class MPU6500:
    def __init__(self, bus=1, address=0x68, calibration_file=None):
        self.bus = smbus.SMBus(bus)
        self.address = address
        
        # MPU6500 Register Map
        self.PWR_MGMT_1 = 0x6B
        self.GYRO_CONFIG = 0x1B
        self.ACCEL_CONFIG = 0x1C
        self.ACCEL_XOUT_H = 0x3B
        self.GYRO_XOUT_H = 0x43
        self.SMPLRT_DIV = 0x19
        self.CONFIG = 0x1A
        
        # Calibration data
        self.accel_offsets = np.array([0.0, 0.0, 0.0])
        self.gyro_offsets = np.array([0.0, 0.0, 0.0])
        
        # Madgwick filter parameters
        self.beta = 0.1  # Filter gain
        self.q = np.array([1.0, 0.0, 0.0, 0.0])  # Quaternion
        self.last_time = time.time()
        
        # Initialize the sensor
        self.initialize()
        
        # Load calibration if available
        if calibration_file:
            self.load_calibration(calibration_file)
        
    def initialize(self):
        # Wake up the sensor
        self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        
        # Configure gyroscope range (±2000°/s)
        self.bus.write_byte_data(self.address, self.GYRO_CONFIG, 0x18)
        
        # Configure accelerometer range (±16g)
        self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0x18)
        
        # Set sample rate divider (1kHz / (1 + 7) = 125Hz)
        self.bus.write_byte_data(self.address, self.SMPLRT_DIV, 0x07)
        
        # Configure digital low pass filter (DLPF_CFG = 6, bandwidth = 5Hz)
        self.bus.write_byte_data(self.address, self.CONFIG, 0x06)
        
        time.sleep(0.1)
        
    def read_word_2c(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val
            
    def read_all(self):
        # Read accelerometer data
        accel_x = self.read_word_2c(self.ACCEL_XOUT_H) / 2048.0
        accel_y = self.read_word_2c(self.ACCEL_XOUT_H + 2) / 2048.0
        accel_z = self.read_word_2c(self.ACCEL_XOUT_H + 4) / 2048.0
        
        # Read gyroscope data
        gyro_x = self.read_word_2c(self.GYRO_XOUT_H) / 16.4
        gyro_y = self.read_word_2c(self.GYRO_XOUT_H + 2) / 16.4
        gyro_z = self.read_word_2c(self.GYRO_XOUT_H + 4) / 16.4
        
        # Apply calibration offsets
        accel_data = np.array([accel_x, accel_y, accel_z]) - self.accel_offsets
        gyro_data = np.array([gyro_x, gyro_y, gyro_z]) - self.gyro_offsets
        
        return gyro_data, accel_data
        
    def calibrate(self, samples=1000):
        """Calibrate the IMU by collecting samples while stationary"""
        print("Calibrating IMU. Keep the device still...")
        
        accel_readings = []
        gyro_readings = []
        
        for _ in range(samples):
            gyro_data, accel_data = self.read_all()
            accel_readings.append(accel_data)
            gyro_readings.append(gyro_data)
            time.sleep(0.01)
            
        # Calculate mean offsets
        self.accel_offsets = np.mean(accel_readings, axis=0)
        self.gyro_offsets = np.mean(gyro_readings, axis=0)
        
        # Z-axis of accelerometer should read 1g when level
        self.accel_offsets[2] = self.accel_offsets[2] - 1.0
        
        print("Calibration complete!")
        print(f"Accelerometer offsets: {self.accel_offsets}")
        print(f"Gyroscope offsets: {self.gyro_offsets}")
        
        return self.accel_offsets, self.gyro_offsets
        
    def save_calibration(self, filename="imu_calibration.json"):
        """Save calibration data to a file"""
        calibration_data = {
            "accel_offsets": self.accel_offsets.tolist(),
            "gyro_offsets": self.gyro_offsets.tolist()
        }
        
        with open(filename, 'w') as f:
            json.dump(calibration_data, f)
            
    def load_calibration(self, filename="imu_calibration.json"):
        """Load calibration data from a file"""
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
                
            self.accel_offsets = np.array(calibration_data["accel_offsets"])
            self.gyro_offsets = np.array(calibration_data["gyro_offsets"])
            return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False
            
    def madgwick_update(self, gyro_data, accel_data, dt):
        """Update quaternion using Madgwick filter"""
        q1, q2, q3, q4 = self.q
        
        # Normalize accelerometer measurement
        accel_norm = np.linalg.norm(accel_data)
        if accel_norm != 0:
            accel_data = accel_data / accel_norm
            
        # Gradient descent algorithm
        f = np.array([
            2*(q2*q4 - q1*q3) - accel_data[0],
            2*(q1*q2 + q3*q4) - accel_data[1],
            2*(0.5 - q2*q2 - q3*q3) - accel_data[2]
        ])
        
        j = np.array([
            [-2*q3, 2*q4, -2*q1, 2*q2],
            [2*q2, 2*q1, 2*q4, 2*q3],
            [0, -4*q2, -4*q3, 0]
        ])
        
        step = j.T.dot(f)
        step_norm = np.linalg.norm(step)
        if step_norm != 0:
            step = step / step_norm
            
        # Compute rate of change of quaternion
        q_dot = 0.5 * np.array([
            -q2*gyro_data[0] - q3*gyro_data[1] - q4*gyro_data[2],
            q1*gyro_data[0] + q3*gyro_data[2] - q4*gyro_data[1],
            q1*gyro_data[1] - q2*gyro_data[2] + q4*gyro_data[0],
            q1*gyro_data[2] + q2*gyro_data[1] - q3*gyro_data[0]
        ])
        
        # Apply feedback
        q_dot = q_dot - self.beta * step
        
        # Integrate to yield quaternion
        self.q = self.q + q_dot * dt
        
        # Normalize quaternion
        self.q = self.q / np.linalg.norm(self.q)
        
    def compute_angles(self, accel_data, gyro_data):
        """Compute roll, pitch, and yaw using Madgwick filter"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Update Madgwick filter
        self.madgwick_update(gyro_data, accel_data, dt)
        
        # Extract angles from quaternion
        q1, q2, q3, q4 = self.q
        
        # Calculate roll, pitch, and yaw
        roll = math.atan2(2*(q1*q2 + q3*q4), 1-2*(q2*q2 + q3*q3)) * 180/math.pi
        pitch = math.asin(2*(q1*q3 - q4*q2)) * 180/math.pi
        yaw = math.atan2(2*(q1*q4 + q2*q3), 1-2*(q3*q3 + q4*q4)) * 180/math.pi
        
        return roll, pitch, yaw
        
    def get_quaternion(self):
        """Return the current quaternion"""
        return self.q
        
    def get_linear_acceleration(self, accel_data):
        """Return linear acceleration (without gravity)"""
        # Convert quaternion to rotation matrix
        q1, q2, q3, q4 = self.q
        rot_matrix = np.array([
            [1-2*(q2*q2+q3*q3), 2*(q1*q2-q3*q4), 2*(q1*q3+q2*q4)],
            [2*(q1*q2+q3*q4), 1-2*(q1*q1+q3*q3), 2*(q2*q3-q1*q4)],
            [2*(q1*q3-q2*q4), 2*(q2*q3+q1*q4), 1-2*(q1*q1+q2*q2)]
        ])
        
        # Remove gravity from accelerometer data
        gravity = np.array([0, 0, 1])
        gravity_rotated = rot_matrix.T.dot(gravity)
        linear_accel = accel_data - gravity_rotated
        
        return linear_accel

if __name__ == "__main__":
    # Simple test program
    imu = MPU6050()
    
    # Calibrate and save
    imu.calibrate()
    imu.save_calibration()
    
    # Test readings
    print("Testing sensor readings:")
    for _ in range(10):
        gyro_data, accel_data = imu.read_all()
        roll, pitch, yaw = imu.compute_angles(accel_data, gyro_data)
        print(f"Roll: {roll:.2f}°, Pitch: {pitch:.2f}°, Yaw: {yaw:.2f}°")
        time.sleep(0.1) 