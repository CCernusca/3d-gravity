import pygame
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
    
    # Perspective projection with safety checks
    if cam_z <= 1e8:  # Prevent division by zero (much smaller threshold)
        cam_z = 1e8
    
    # Check for NaN values and handle them
    if not np.isfinite(cam_x) or not np.isfinite(cam_y) or not np.isfinite(cam_z):
        return None, None, None, None
    
    # Field of view based scaling
    fov_factor = 500.0  # Adjust this for zoom level
    scale = fov_factor / cam_z
    
    # Check scale for NaN or infinite values
    if not np.isfinite(scale):
        return None, None, None, None
    
    # Project to screen coordinates
    screen_x = int(width / 2 + cam_x * scale)
    screen_y = int(height / 2 - cam_y * scale)
    
    # Final check for valid screen coordinates
    if not np.isfinite(screen_x) or not np.isfinite(screen_y):
        return None, None, None, None
    
    return screen_x, screen_y, cam_z, scale


def check_hover(mouse_pos, bodies, camera, width, height):
    """Check if mouse is hovering over any body"""
    mouse_x, mouse_y = mouse_pos
    
    for body in bodies:
        proj_x, proj_y, cam_z, scale = project_3d_to_2d(body.position, camera, width, height)
        
        # Skip if projection failed
        if proj_x is None or proj_y is None or cam_z is None or scale is None:
            continue
        
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


def handle_locked_camera_input(camera, keys, movement_speed_multiplier=1.0, locked_body=None):
    """Handle camera input when locked to a body - allows orbital movement"""
    if not locked_body or not hasattr(camera, 'lock_offset'):
        return
    
    # Calculate forward vector (from camera to planet)
    direction_to_body = locked_body.position - camera.position
    if np.linalg.norm(direction_to_body) > 0:
        forward = direction_to_body / np.linalg.norm(direction_to_body)
    else:
        forward = np.array([0, 0, 1])
    
    # Calculate right and up vectors from forward
    # Right is perpendicular to forward and world up
    world_up = np.array([0, 1, 0])
    right = np.cross(world_up, forward)
    if np.linalg.norm(right) > 0:
        right = right / np.linalg.norm(right)
    else:
        # If looking straight up/down, use different right vector
        right = np.array([1, 0, 0])
    
    # Up is perpendicular to forward and right
    up = np.cross(forward, right)
    if np.linalg.norm(up) > 0:
        up = up / np.linalg.norm(up)
    
    # Orbital movement (WASD) - move camera around the body
    orbital_speed = camera.move_speed * movement_speed_multiplier
    
    if keys[K_w]:
        # Move up (orbit vertically) - INVERTED
        camera.lock_offset -= up * orbital_speed
    if keys[K_s]:
        # Move down (orbit vertically) - INVERTED
        camera.lock_offset += up * orbital_speed
    if keys[K_a]:
        # Move left (orbit horizontally)
        camera.lock_offset -= right * orbital_speed
    if keys[K_d]:
        # Move right (orbit horizontally)
        camera.lock_offset += right * orbital_speed
    
    # Zoom (QE) - move closer/further from body
    zoom_speed = camera.zoom_speed * movement_speed_multiplier
    
    if keys[K_q]:
        # Zoom out (move further away)
        direction = camera.lock_offset / np.linalg.norm(camera.lock_offset) if np.linalg.norm(camera.lock_offset) > 0 else np.array([0, 0, 1])
        camera.lock_offset += direction * zoom_speed
    if keys[K_e]:
        # Zoom in (move closer)
        direction = camera.lock_offset / np.linalg.norm(camera.lock_offset) if np.linalg.norm(camera.lock_offset) > 0 else np.array([0, 0, 1])
        camera.lock_offset -= direction * zoom_speed
        
        # Prevent getting too close
        min_distance = 1e10  # Minimum distance from body
        current_distance = np.linalg.norm(camera.lock_offset)
        if current_distance < min_distance or not np.isfinite(current_distance):
            if current_distance > 0 and np.isfinite(current_distance):
                direction_norm = camera.lock_offset / current_distance
                camera.lock_offset = direction_norm * min_distance
            else:
                # Reset to safe distance if lock_offset is invalid
                camera.lock_offset = np.array([0, 0, min_distance])
    
    # Calculate pitch and yaw to always look at the planet
    if np.linalg.norm(direction_to_body) > 0:
        # Calculate yaw from forward vector
        yaw = np.arctan2(forward[0], forward[2])
        
        # Calculate pitch from forward vector
        horizontal_dist = np.sqrt(forward[0]**2 + forward[2]**2)
        pitch = np.arctan2(-forward[1], horizontal_dist)
        
        # Apply rotation to camera
        camera.yaw = yaw
        camera.pitch = pitch
        camera._update_vectors()


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
