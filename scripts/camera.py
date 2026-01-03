import numpy as np
from pygame.locals import *


class Camera:
    def __init__(self):
        self.position = np.array([0.0, 0.0, -11e11])  # Start camera back from origin
        self.yaw = 0.0  # Rotation around global up vector (Y)
        self.pitch = 0.0  # Rotation around local right vector
        self.move_speed = 1e10
        self.zoom_speed = 1e10
        self.fov = 60  # Field of view in degrees
        
        # Update rotation array for compatibility
        self.rotation = np.array([self.pitch, self.yaw])
        self._update_vectors()
    
    def _update_vectors(self):
        """Update camera vectors based on current yaw and pitch"""
        # Yaw around global Y axis
        cos_yaw, sin_yaw = np.cos(self.yaw), np.sin(self.yaw)
        
        # Forward vector (after yaw)
        forward_yaw = np.array([
            sin_yaw,
            0,
            cos_yaw
        ])
        
        # Right vector (global, perpendicular to forward yaw)
        self.right = np.array([
            cos_yaw,
            0,
            -sin_yaw
        ])
        
        # Apply pitch around local right vector
        cos_pitch, sin_pitch = np.cos(self.pitch), np.sin(self.pitch)
        
        # Final forward vector after both rotations
        self.forward = np.array([
            forward_yaw[0] * cos_pitch,
            -sin_pitch,
            forward_yaw[2] * cos_pitch
        ])
        
        # Up vector (cross product)
        self.up = np.cross(self.right, self.forward)
        
        # Update rotation array for compatibility
        self.rotation = np.array([self.pitch, self.yaw])
    
    def get_forward_vector(self):
        return self.forward / np.linalg.norm(self.forward)
    
    def get_right_vector(self):
        return self.right / np.linalg.norm(self.right)
    
    def get_up_vector(self):
        return self.up / np.linalg.norm(self.up)
    
    def move(self, direction, speed_multiplier=1.0):
        """Move camera in world space relative to its orientation"""
        forward = self.get_forward_vector()
        right = self.get_right_vector()
        up = self.get_up_vector()
        
        actual_speed = self.move_speed * speed_multiplier
        
        if direction == 'forward':
            self.position += forward * actual_speed
        elif direction == 'backward':
            self.position -= forward * actual_speed
        elif direction == 'left':
            self.position -= right * actual_speed
        elif direction == 'right':
            self.position += right * actual_speed
        elif direction == 'up':
            self.position += up * actual_speed
        elif direction == 'down':
            self.position -= up * actual_speed
        elif direction == 'zoom_in':
            # Move forward faster for zoom
            self.position += forward * self.zoom_speed
        elif direction == 'zoom_out':
            # Move backward faster for zoom
            self.position -= forward * self.zoom_speed
    
    def rotate(self, dx, dy):
        """Rotate camera view - yaw around global up, pitch around local right"""
        self.yaw += dx  # Yaw around global up vector
        self.pitch -= dy  # Pitch around local right vector (inverted)
        self._update_vectors()  # Update all vectors


def project_3d_to_2d(pos_3d, camera, width, height):
    """Proper 3D to 2D projection with camera transformation"""
    # Transform to camera space (translate)
    relative_pos = pos_3d - camera.position
    
    # Transform to camera space using camera vectors
    x, y, z = relative_pos
    
    # Get camera axes
    right = camera.get_right_vector()
    up = camera.get_up_vector()
    forward = camera.get_forward_vector()
    
    # Transform to camera coordinates (dot products)
    cam_x = np.dot(relative_pos, right)
    cam_y = np.dot(relative_pos, up)
    cam_z = np.dot(relative_pos, forward)
    
    # Perspective projection
    if cam_z <= 1e8:  # Prevent division by zero (much smaller threshold)
        cam_z = 1e8
    
    # Field of view based scaling
    fov_factor = 500.0  # Adjust this for zoom level
    scale = fov_factor / cam_z
    
    # Project to screen coordinates
    screen_x = int(width / 2 + cam_x * scale)
    screen_y = int(height / 2 - cam_y * scale)
    
    return screen_x, screen_y, cam_z, scale


def check_hover(mouse_pos, bodies, camera, width, height):
    """Check if mouse is hovering over any body"""
    mouse_x, mouse_y = mouse_pos
    
    for body in bodies:
        proj_x, proj_y, cam_z, scale = project_3d_to_2d(body.position, camera, width, height)
        
        # Check if projection is valid and body is visible
        if (isinstance(proj_x, (int, float)) and isinstance(proj_y, (int, float)) and
            cam_z > 0 and -100 <= proj_x <= width + 100 and 
            -100 <= proj_y <= height + 100):
            
            # Calculate screen radius for hover detection
            screen_radius = max(10, int(body.radius * scale))
            
            # Check if mouse is within body radius
            distance = ((mouse_x - proj_x) ** 2 + (mouse_y - proj_y) ** 2) ** 0.5
            if distance <= screen_radius:
                return body
    
    return None


def handle_camera_input(camera, keys, movement_speed_multiplier=1.0):
    """Handle camera control input"""
    # Rotation
    if keys[K_LEFT]:
        camera.rotate(-0.02, 0)
    if keys[K_RIGHT]:
        camera.rotate(0.02, 0)
    if keys[K_UP]:
        camera.rotate(0, -0.02)
    if keys[K_DOWN]:
        camera.rotate(0, 0.02)
    
    # Pan camera (WASD) with speed multiplier
    if keys[K_w]:
        camera.move('up', movement_speed_multiplier)
    if keys[K_s]:
        camera.move('down', movement_speed_multiplier)
    if keys[K_a]:
        camera.move('left', movement_speed_multiplier)
    if keys[K_d]:
        camera.move('right', movement_speed_multiplier)
    
    # Zoom (Q/E) with speed multiplier
    if keys[K_q]:
        camera.move('backward', movement_speed_multiplier)
    if keys[K_e]:
        camera.move('forward', movement_speed_multiplier)
