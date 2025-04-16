#!/usr/bin/env python3

class PID:
    """
    A simple PID controller class.
    
    PID (Proportional, Integral, Derivative) controllers are used to 
    control the output of a system to reach a desired setpoint.
    """
    
    def __init__(self, kp, ki, kd, output_limit_min=None, output_limit_max=None):
        """
        Initialize the PID controller with the specified gains.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limit_min: Minimum output value (None for no limit)
            output_limit_max: Maximum output value (None for no limit)
        """
        # PID gains
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # Output limits
        self.output_limit_min = output_limit_min
        self.output_limit_max = output_limit_max
        
        # State variables
        self.last_error = 0.0
        self.integral = 0.0
        
        # Anti-windup protection (limit integral accumulation)
        self.integral_limit = 200.0
        
    def update(self, error, dt):
        """
        Update the PID controller with the current error and time step.
        
        Args:
            error: Current error (setpoint - measurement)
            dt: Time step in seconds
            
        Returns:
            The PID controller output
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term with anti-windup
        self.integral += error * dt
        self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
        i_term = self.ki * self.integral
        
        # Derivative term (on measurement, not error)
        d_term = self.kd * (error - self.last_error) / dt if dt > 0 else 0
        self.last_error = error
        
        # Calculate output
        output = p_term + i_term + d_term
        
        # Apply output limits if specified
        if self.output_limit_min is not None and self.output_limit_max is not None:
            output = max(min(output, self.output_limit_max), self.output_limit_min)
            
        return output
        
    def reset(self):
        """Reset the PID controller state."""
        self.last_error = 0.0
        self.integral = 0.0
        
    def set_gains(self, kp=None, ki=None, kd=None):
        """Update the PID gains."""
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
            
    def set_output_limits(self, output_min, output_max):
        """Set the output limits of the PID controller."""
        self.output_limit_min = output_min
        self.output_limit_max = output_max 