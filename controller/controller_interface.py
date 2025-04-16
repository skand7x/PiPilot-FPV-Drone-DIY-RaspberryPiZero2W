#!/usr/bin/env python3
import pygame
import time
import os
import threading
import sys
import json
import math

class ControllerInterface:
    """
    Interface for game controllers (Xbox, etc.) using pygame
    Also supports mobile control via WiFi through a simple web server
    """
    
    def __init__(self, controller_type="xbox", config_file=None):
        """
        Initialize the controller interface.
        
        Args:
            controller_type: Type of controller ('xbox' or 'mobile')
            config_file: Optional path to a config file
        """
        self.controller_type = controller_type.lower()
        self.connected = False
        self.input_data = {
            'left_x': 0.0,  # Left stick X axis (-1 to 1)
            'left_y': 0.0,  # Left stick Y axis (-1 to 1)
            'right_x': 0.0, # Right stick X axis (-1 to 1)
            'right_y': 0.0, # Right stick Y axis (-1 to 1)
            'start_pressed': False,  # Start button
            'back_pressed': False,   # Back/Select button
            'a_pressed': False,      # A button
            'b_pressed': False,      # B button
            'x_pressed': False,      # X button
            'y_pressed': False,      # Y button
            'lb_pressed': False,     # Left bumper
            'rb_pressed': False,     # Right bumper
            'lt_value': 0.0,         # Left trigger (0 to 1)
            'rt_value': 0.0,         # Right trigger (0 to 1)
        }
        
        # Load configuration if provided
        self.config = {}
        if config_file:
            self._load_config(config_file)
        
        # Initialize based on controller type
        if self.controller_type == 'xbox':
            self._init_xbox_controller()
        elif self.controller_type == 'mobile':
            self._init_mobile_controller()
        else:
            print(f"Unsupported controller type: {controller_type}")
            print("Defaulting to Xbox controller")
            self.controller_type = 'xbox'
            self._init_xbox_controller()
            
        # Start update thread
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def _load_config(self, config_file):
        """Load controller configuration from file"""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            print(f"Loaded controller config from {config_file}")
        except Exception as e:
            print(f"Error loading controller config: {e}")
            self.config = {}
    
    def _init_xbox_controller(self):
        """Initialize the Xbox controller using pygame"""
        try:
            # Initialize pygame and the joystick module
            pygame.init()
            pygame.joystick.init()
            
            # Check if any joysticks/controllers are connected
            if pygame.joystick.get_count() > 0:
                # Initialize the first joystick
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                self.connected = True
                print(f"Connected to controller: {self.controller.get_name()}")
            else:
                print("No controllers found. Connect an Xbox controller and try again.")
                self.connected = False
                
        except Exception as e:
            print(f"Error initializing Xbox controller: {e}")
            self.connected = False
    
    def _init_mobile_controller(self):
        """Initialize the mobile controller via WiFi"""
        try:
            from http.server import BaseHTTPRequestHandler, HTTPServer
            import socket
            
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.ip_address = s.getsockname()[0]
            s.close()
            
            # Define HTTP request handler for mobile interface
            controller_interface = self  # Reference to the outer class
            
            class MobileControllerHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    """Handle GET requests for the web interface"""
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        
                        # Send HTML interface
                        with open(os.path.join(os.path.dirname(__file__), 'mobile_controller.html'), 'rb') as file:
                            self.wfile.write(file.read())
                    elif self.path == '/controller.js':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/javascript')
                        self.end_headers()
                        
                        with open(os.path.join(os.path.dirname(__file__), 'controller.js'), 'rb') as file:
                            self.wfile.write(file.read())
                    elif self.path == '/status':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        
                        self.wfile.write(json.dumps({'connected': True}).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def do_POST(self):
                    """Handle POST requests with controller data"""
                    if self.path == '/update':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        
                        try:
                            data = json.loads(post_data.decode())
                            
                            # Update controller state
                            controller_interface.input_data.update(data)
                            
                            # Send response
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'status': 'ok'}).encode())
                            
                        except Exception as e:
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'error': str(e)}).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                        
                def log_message(self, format, *args):
                    """Suppress HTTP server logs"""
                    return
            
            # Start HTTP server in a separate thread
            self.server = HTTPServer((self.ip_address, 8080), MobileControllerHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.connected = True
            print(f"Mobile controller server started at http://{self.ip_address}:8080")
            print("Connect with your mobile device to control the drone")
            
        except Exception as e:
            print(f"Error initializing mobile controller: {e}")
            self.connected = False
    
    def _update_xbox_controller(self):
        """Update input data from Xbox controller"""
        if not self.connected:
            # Try to reconnect if controller disconnected
            if pygame.joystick.get_count() > 0:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                self.connected = True
                print(f"Reconnected to controller: {self.controller.get_name()}")
            else:
                return
        
        try:
            # Process events to get fresh controller data
            pygame.event.pump()
            
            # Get joystick axes
            self.input_data['left_x'] = self.controller.get_axis(0)
            self.input_data['left_y'] = -self.controller.get_axis(1)  # Invert Y axis
            self.input_data['right_x'] = self.controller.get_axis(2)
            self.input_data['right_y'] = -self.controller.get_axis(3)  # Invert Y axis
            
            # Apply deadzone to prevent drift
            deadzone = 0.1
            for axis in ['left_x', 'left_y', 'right_x', 'right_y']:
                if abs(self.input_data[axis]) < deadzone:
                    self.input_data[axis] = 0.0
                else:
                    # Rescale values to go from 0 to 1 even with deadzone
                    self.input_data[axis] = (self.input_data[axis] - math.copysign(deadzone, self.input_data[axis])) / (1 - deadzone)
            
            # Get trigger values
            self.input_data['lt_value'] = (self.controller.get_axis(4) + 1) / 2.0  # Convert from -1,1 to 0,1
            self.input_data['rt_value'] = (self.controller.get_axis(5) + 1) / 2.0  # Convert from -1,1 to 0,1
            
            # Get button states
            self.input_data['a_pressed'] = self.controller.get_button(0)
            self.input_data['b_pressed'] = self.controller.get_button(1)
            self.input_data['x_pressed'] = self.controller.get_button(2)
            self.input_data['y_pressed'] = self.controller.get_button(3)
            self.input_data['lb_pressed'] = self.controller.get_button(4)
            self.input_data['rb_pressed'] = self.controller.get_button(5)
            self.input_data['back_pressed'] = self.controller.get_button(6)
            self.input_data['start_pressed'] = self.controller.get_button(7)
            
        except Exception as e:
            print(f"Error reading Xbox controller: {e}")
            self.connected = False
            
    def _update_mobile_controller(self):
        """Update input data from mobile controller"""
        # Mobile controller data is updated via HTTP POST requests
        # No additional processing needed here
        pass
        
    def _update_loop(self):
        """Main update loop for the controller"""
        while self.running:
            if self.controller_type == 'xbox':
                self._update_xbox_controller()
            elif self.controller_type == 'mobile':
                self._update_mobile_controller()
                
            time.sleep(0.02)  # 50Hz update rate
    
    def get_input(self):
        """Get the current controller input data"""
        return self.input_data.copy()
    
    def is_connected(self):
        """Check if the controller is connected"""
        return self.connected
    
    def close(self):
        """Close the controller interface"""
        self.running = False
        
        if self.controller_type == 'xbox':
            pygame.quit()
        elif self.controller_type == 'mobile' and hasattr(self, 'server'):
            self.server.shutdown()
            
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
            
        print("Controller interface closed")


if __name__ == "__main__":
    # Simple test program
    controller_type = 'xbox'  # or 'mobile'
    
    if len(sys.argv) > 1:
        controller_type = sys.argv[1]
    
    print(f"Testing {controller_type} controller. Press Ctrl+C to exit.")
    controller = ControllerInterface(controller_type)
    
    try:
        while True:
            data = controller.get_input()
            print(f"\rLeft: ({data['left_x']:.2f}, {data['left_y']:.2f}) "
                  f"Right: ({data['right_x']:.2f}, {data['right_y']:.2f}) "
                  f"LT: {data['lt_value']:.2f} RT: {data['rt_value']:.2f} "
                  f"Start: {data['start_pressed']} Back: {data['back_pressed']}",
                  end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        controller.close() 