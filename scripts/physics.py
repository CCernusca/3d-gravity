import numpy as np

# Physics constants
G = 6.67430e-11  # Gravitational constant (scaled for simulation)
SCALE = 1e9  # Scale factor for distances
DT = 86400  # Time step (1 day in seconds)
FPS = 60

# Default time multiplier
TIME_MULTIPLIER = 1.0


class Body:
    def __init__(self, name, mass, position, velocity, radius, color, inclination=0.0):
        self.name = name
        self.mass = mass
        self.position = np.array(position, dtype=float)  # [x, y, z]
        self.velocity = np.array(velocity, dtype=float)  # [vx, vy, vz]
        self.radius = radius
        self.color = color
        self.inclination = inclination  # Orbital inclination in radians
        self.trail = []
        self.max_trail_length = 100  # Fixed maximum trail length
        self.trail_distance_threshold = 5e9  # Distance threshold for new trail points
        
        # Apply inclination to initial position and velocity
        self._apply_inclination()
    
    def _apply_inclination(self):
        """Apply orbital inclination to position and velocity"""
        if self.inclination != 0:
            # Rotation matrix for inclination around x-axis
            cos_i = np.cos(self.inclination)
            sin_i = np.sin(self.inclination)
            
            # Apply to position (rotate around x-axis)
            y = self.position[1] * cos_i - self.position[2] * sin_i
            z = self.position[1] * sin_i + self.position[2] * cos_i
            self.position[1] = y
            self.position[2] = z
            
            # Apply to velocity (rotate around x-axis)
            vy = self.velocity[1] * cos_i - self.velocity[2] * sin_i
            vz = self.velocity[1] * sin_i + self.velocity[2] * cos_i
            self.velocity[1] = vy
            self.velocity[2] = vz
    
    def update_position(self, acceleration):
        self.velocity += acceleration * DT
        self.position += self.velocity * DT
        
        # Store trail
        self.trail.append(self.position.copy())
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)


def calculate_gravity(body1, body2):
    """Calculate gravitational force between two bodies"""
    r_vec = body2.position - body1.position
    distance = np.linalg.norm(r_vec)
    
    if distance == 0:
        return np.array([0.0, 0.0, 0.0])
    
    # Gravitational force magnitude
    force_mag = G * body1.mass * body2.mass / (distance ** 2)
    
    # Force direction (unit vector)
    force_dir = r_vec / distance
    
    # Force vector
    force = force_mag * force_dir
    
    return force


def update_physics(bodies, time_multiplier=1.0):
    """Update physics for all bodies with time multiplier"""
    effective_dt = DT * time_multiplier
    
    for body in bodies:
        net_force = np.array([0.0, 0.0, 0.0])
        
        for other in bodies:
            if body != other:
                force = calculate_gravity(body, other)
                net_force += force
        
        # Calculate acceleration (F = ma)
        acceleration = net_force / body.mass
        
        # Update with effective time step
        body.velocity += acceleration * effective_dt
        body.position += body.velocity * effective_dt
        
        # Distance-based trail generation with intermediate points
        if len(body.trail) == 0:
            # First trail point
            body.trail.append(body.position.copy())
        else:
            # Check distance from last trail point
            last_point = body.trail[-1]
            distance = np.linalg.norm(body.position - last_point)
            
            if distance >= body.trail_distance_threshold:
                # Add intermediate points if distance is very large
                remaining_distance = distance
                direction = (body.position - last_point) / distance  # Unit vector
                
                while remaining_distance >= body.trail_distance_threshold:
                    # Add point at threshold distance along the path
                    intermediate_point = last_point + direction * body.trail_distance_threshold
                    body.trail.append(intermediate_point)
                    last_point = intermediate_point
                    remaining_distance -= body.trail_distance_threshold
                
                # Add final point if there's remaining distance
                if remaining_distance > 0:
                    body.trail.append(body.position.copy())
        
        # Maintain fixed trail length
        while len(body.trail) > body.max_trail_length:
            body.trail.pop(0)
