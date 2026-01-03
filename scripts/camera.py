import pygame
import numpy as np
from pygame.locals import *


class Camera:
    def __init__(self, position=None, forward=None, up=None):
        """Initialize camera with position and orientation vectors"""
        # Position
        if position is None:
            self.position = np.array([0.0, 0.0, -5e11])  # Default position
        else:
            self.position = np.array(position, dtype=float)
        
        # Orientation vectors (always normalized)
        if forward is None:
            self.forward = np.array([0.0, 0.0, 1.0])  # Default forward (looking along +Z)
        else:
            self.forward = forward / np.linalg.norm(forward)
        
        if up is None:
            self.up = np.array([0.0, 1.0, 0.0])  # Default up (along +Y)
        else:
            self.up = up / np.linalg.norm(up)
        
        # Calculate right vector from forward and up (ensures orthogonality)
        self.right = np.cross(self.up, self.forward)
        if np.linalg.norm(self.right) > 0:
            self.right = self.right / np.linalg.norm(self.right)
        else:
            # Fallback if forward and up are parallel
            self.right = np.array([1.0, 0.0, 0.0])
            self.up = np.cross(self.forward, self.right)
            self.up = self.up / np.linalg.norm(self.up)
        
        # Movement speeds
        self.move_speed = 1e10  # Base movement speed
        self.zoom_speed = 5e10  # Zoom speed
    
    def get_forward_vector(self):
        """Get normalized forward vector"""
        return self.forward
    
    def get_right_vector(self):
        """Get normalized right vector"""
        return self.right
    
    def get_up_vector(self):
        """Get normalized up vector"""
        return self.up
    
    def rotate(self, axis, angle):
        """Rotate camera around arbitrary axis using Rodrigues' formula"""
        axis = axis / np.linalg.norm(axis)  # Ensure axis is normalized
        
        # Rotate all three vectors
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)
        
        def rotate_vector(v):
            return (
                v * cos_angle +
                np.cross(axis, v) * sin_angle +
                axis * np.dot(axis, v) * (1 - cos_angle)
            )
        
        self.forward = rotate_vector(self.forward)
        self.up = rotate_vector(self.up)
        self.right = rotate_vector(self.right)
        
        # Renormalize to prevent drift
        self.forward = self.forward / np.linalg.norm(self.forward)
        self.up = self.up / np.linalg.norm(self.up)
        self.right = self.right / np.linalg.norm(self.right)
    
    def rotate_yaw(self, angle):
        """Rotate camera around world up (Y) axis"""
        # Use Rodrigues' formula to rotate forward and right vectors around world up
        world_up = np.array([0, 1, 0])
        
        # Rotate forward vector
        self.forward = _rotate_vector_around_axis(self.forward, world_up, angle)
        self.forward = self.forward / np.linalg.norm(self.forward)
        
        # Rotate right vector
        self.right = _rotate_vector_around_axis(self.right, world_up, angle)
        self.right = self.right / np.linalg.norm(self.right)
        
        # Recalculate up to maintain orthogonal system
        self.up = np.cross(self.forward, self.right)
        self.up = self.up / np.linalg.norm(self.up)
    
    def rotate_pitch(self, angle):
        """Rotate camera around local right axis"""
        # Use Rodrigues' formula to rotate forward and up vectors around right
        right_normalized = self.right / np.linalg.norm(self.right)
        
        # Rotate forward vector
        self.forward = _rotate_vector_around_axis(self.forward, right_normalized, angle)
        self.forward = self.forward / np.linalg.norm(self.forward)
        
        # Rotate up vector
        self.up = _rotate_vector_around_axis(self.up, right_normalized, angle)
        self.up = self.up / np.linalg.norm(self.up)
        
        # Recalculate right to maintain orthogonal system
        self.right = np.cross(self.up, self.forward)
        self.right = self.right / np.linalg.norm(self.right)
    
    
    def rotate_roll(self, angle):
        """Rotate camera around local forward axis"""
        forward_normalized = self.forward / np.linalg.norm(self.forward)
        
        # Rotate right vector
        self.right = _rotate_vector_around_axis(self.right, forward_normalized, angle)
        self.right = self.right / np.linalg.norm(self.right)
        
        # Rotate up vector
        self.up = _rotate_vector_around_axis(self.up, forward_normalized, angle)
        self.up = self.up / np.linalg.norm(self.up)
        
        # Recalculate forward to maintain orthogonal system
        self.forward = np.cross(self.right, self.up)
        self.forward = self.forward / np.linalg.norm(self.forward)

    
    def reset_rotation(self):
        """Reset camera to default orientation (forward along +Z, up along +Y)"""
        # Reset to default orientation vectors
        self.forward = np.array([0.0, 0.0, 1.0])  # Looking along +Z
        self.up = np.array([0.0, 1.0, 0.0])        # Up along +Y
        self.right = np.array([1.0, 0.0, 0.0])      # Right along +X
        
        # Ensure all vectors are normalized (they should be already)
        self.forward = self.forward / np.linalg.norm(self.forward)
        self.up = self.up / np.linalg.norm(self.up)
        self.right = self.right / np.linalg.norm(self.right)
    
    def get_yaw(self):
        """Get yaw angle for UI display only"""
        return np.arctan2(self.forward[0], self.forward[2])
    
    def get_pitch(self):
        """Get pitch angle for UI display only"""
        horizontal_dist = np.sqrt(self.forward[0]**2 + self.forward[2]**2)
        return np.arctan2(-self.forward[1], horizontal_dist)
    
    def get_roll(self):
        """Get roll angle for UI display only"""
        expected_up = np.array([
            -np.sin(self.get_pitch()) * np.sin(self.get_yaw()),
            np.cos(self.get_pitch()),
            -np.sin(self.get_pitch()) * np.cos(self.get_yaw())
        ])
        
        if np.linalg.norm(expected_up) > 0 and np.linalg.norm(self.up) > 0:
            expected_up = expected_up / np.linalg.norm(expected_up)
            up_normalized = self.up / np.linalg.norm(self.up)
            roll_cos = np.clip(np.dot(expected_up, up_normalized), -1, 1)
            roll = np.arccos(roll_cos)
            
            # Determine roll direction
            cross_product = np.cross(expected_up, up_normalized)
            if np.dot(cross_product, self.forward) < 0:
                roll = -roll
        else:
            roll = 0
        
        return roll
    
    
    def move(self, direction, speed_multiplier=1.0):
        """Move camera in specified direction"""
        move_distance = self.move_speed * speed_multiplier
        
        if direction == 'forward':
            self.position += self.forward * move_distance
        elif direction == 'backward':
            self.position -= self.forward * move_distance
        elif direction == 'right':
            self.position += self.right * move_distance
        elif direction == 'left':
            self.position -= self.right * move_distance
        elif direction == 'up':
            self.position += self.up * move_distance
        elif direction == 'down':
            self.position -= self.up * move_distance
    
    def get_angles_for_display(self):
        """Get yaw, pitch, roll angles for UI display only"""
        # Yaw: angle around world Y axis
        yaw = np.arctan2(self.forward[0], self.forward[2])
        
        # Pitch: angle from horizontal plane
        horizontal_dist = np.sqrt(self.forward[0]**2 + self.forward[2]**2)
        pitch = np.arctan2(-self.forward[1], horizontal_dist)
        
        # Roll: angle between actual up and expected up
        expected_up = np.array([
            -np.sin(pitch) * np.sin(yaw),
            np.cos(pitch),
            -np.sin(pitch) * np.cos(yaw)
        ])
        
        if np.linalg.norm(expected_up) > 0 and np.linalg.norm(self.up) > 0:
            expected_up = expected_up / np.linalg.norm(expected_up)
            up_normalized = self.up / np.linalg.norm(self.up)
            roll_cos = np.clip(np.dot(expected_up, up_normalized), -1, 1)
            roll = np.arccos(roll_cos)
            
            # Determine roll direction
            cross_product = np.cross(expected_up, up_normalized)
            if np.dot(cross_product, self.forward) < 0:
                roll = -roll
        else:
            roll = 0
        
        return yaw, pitch, roll
    
    def look_at(self, target):
        """Point camera towards target position"""
        direction = target - self.position
        if np.linalg.norm(direction) > 0:
            self.forward = direction / np.linalg.norm(direction)
            
            # Calculate right and up vectors
            world_up = np.array([0, 1, 0])
            self.right = np.cross(world_up, self.forward)
            if np.linalg.norm(self.right) > 0:
                self.right = self.right / np.linalg.norm(self.right)
            else:
                # Looking straight up/down
                self.right = np.array([1, 0, 0])
            
            self.up = np.cross(self.forward, self.right)
            self.up = self.up / np.linalg.norm(self.up)


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
        # Move up (orbit vertically)
        camera.lock_offset += up * orbital_speed
    if keys[K_s]:
        # Move down (orbit vertically)
        camera.lock_offset -= up * orbital_speed
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
    
    # Use vector-based look_at to always point at the planet
    camera.look_at(locked_body.position)


def get_planetary_coordinates(camera, planetary_body):
    """Calculate latitude/longitude coordinates of camera relative to planetary body"""
    if not planetary_body:
        return None, None, None, None
    
    # Calculate anchor vector from body to camera
    anchor_vector = camera.position - planetary_body.position
    distance = np.linalg.norm(anchor_vector)
    
    if distance == 0:
        return None, None, None, None
    
    # In planetary mode, the anchor vector should point from body to camera
    # We can derive coordinates from the planetary coordinate system
    
    # The up vector in planetary mode points away from the body
    # The right vector is tangential to the surface
    # The forward vector completes the system
    
    # Calculate position in planetary coordinate system
    # Since we're at fixed distance, we can use the anchor direction
    anchor_normalized = anchor_vector / distance
    
    # Calculate latitude from the up component (Y axis)
    latitude = np.degrees(np.arcsin(np.clip(anchor_normalized[1], -1, 1)))
    
    # Calculate longitude from the XZ components
    longitude = np.degrees(np.arctan2(anchor_normalized[0], anchor_normalized[2]))
    
    # Calculate altitude above surface
    altitude = distance - planetary_body.radius
    
    return latitude, longitude, altitude, distance


def _rotate_vector_around_axis(vector, axis, angle):
    """Rotate vector around axis using Rodrigues' formula"""
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    
    return (
        vector * cos_angle +
        np.cross(axis, vector) * sin_angle +
        axis * np.dot(axis, vector) * (1 - cos_angle)
    )


def _rotate_vector_around_axis(vector, axis, angle):
    """Rotate vector around axis using Rodrigues' formula"""
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    
    return (
        vector * cos_angle +
        np.cross(axis, vector) * sin_angle +
        axis * np.dot(axis, vector) * (1 - cos_angle)
    )


def handle_planetary_input(camera, keys, movement_speed_multiplier=1.0, planetary_body=None):
    """Handle camera input in planetary mode - pure vector-based system
    
    PLAN:
    1. Initialize planetary coordinate system vectors
    2. Apply WASD movement around planetary body using vectors
    3. Apply arrow key rotation using vectors directly
    4. Update camera orientation from planetary vectors
    5. Fix distance to planetary body
    """
    if not planetary_body:
        return
    
    # === SECTION 1: INITIALIZATION ===
    # Calculate anchor vector from camera to body
    anchor_vector = planetary_body.position - camera.position
    current_distance = np.linalg.norm(anchor_vector)
    
    if current_distance == 0:
        return
    
    # Normalize anchor vector (points from camera to body)
    anchor_normalized = anchor_vector / current_distance
    
    # Initialize planetary coordinate system if needed
    if not hasattr(camera, 'planetary_right'):
        # Initialize planetary coordinate system
        world_up = np.array([0, 1, 0])
        camera.planetary_right = np.cross(world_up, anchor_normalized)
        if np.linalg.norm(camera.planetary_right) > 0:
            camera.planetary_right = camera.planetary_right / np.linalg.norm(camera.planetary_right)
        else:
            camera.planetary_right = np.array([1, 0, 0])
        
        # SAFE FIX: Use cross product but ensure it's not zero
        camera.planetary_up = np.cross(anchor_normalized, camera.planetary_right)
        if np.linalg.norm(camera.planetary_up) > 1e-6:
            camera.planetary_up = camera.planetary_up / np.linalg.norm(camera.planetary_up)
        else:
            # Fallback: use negative anchor_normalized (points away from planet)
            camera.planetary_up = -anchor_normalized
            if np.linalg.norm(camera.planetary_up) > 0:
                camera.planetary_up = camera.planetary_up / np.linalg.norm(camera.planetary_up)
            else:
                camera.planetary_up = np.array([0, 1, 0])
        
        # Initialize manual rotation vectors (identity)
        camera.manual_rotation = np.eye(3)  # 3x3 identity matrix
    
    # === SECTION 2: MOVEMENT ===
    # Movement speed (angular velocity around the planet)
    angular_speed = 0.02 * movement_speed_multiplier
    
    # A/D: Rotate camera position around planetary up vector (horizontal movement)
    if keys[K_a] or keys[K_d]:
        rotation_dir = -1 if keys[K_d] else 1 # D=negative, A=positive
        angle = angular_speed * rotation_dir
        
        # Rotate position around planetary up vector
        relative_pos = camera.position - planetary_body.position
        new_relative_pos = _rotate_vector_around_axis(
            relative_pos, camera.planetary_up, angle
        )
        camera.position = planetary_body.position + new_relative_pos
        
        # Rotate planetary coordinate system
        camera.planetary_right = _rotate_vector_around_axis(
            camera.planetary_right, camera.planetary_up, angle
        )
        camera.planetary_right = camera.planetary_right / np.linalg.norm(camera.planetary_right)
    
    # W/S: Rotate camera position around right vector (vertical movement)
    if keys[K_w] or keys[K_s]:
        rotation_dir = -1 if keys[K_s] else 1  # S=negative, W=positive
        angle = angular_speed * rotation_dir
        
        # Rotate position around right vector
        relative_pos = camera.position - planetary_body.position
        new_relative_pos = _rotate_vector_around_axis(
            relative_pos, camera.planetary_right, angle
        )
        camera.position = planetary_body.position + new_relative_pos
        
        # Rotate planetary coordinate system
        camera.planetary_up = _rotate_vector_around_axis(
            camera.planetary_up, camera.planetary_right, angle
        )
        camera.planetary_up = camera.planetary_up / np.linalg.norm(camera.planetary_up)
    
    # === SECTION 3: MANUAL ROTATION ===
    # Apply arrow key rotations to manual rotation matrix
    # IMPORTANT: Apply rotations in consistent order to avoid unwanted roll
    
    # Create rotation matrices for this frame
    yaw_matrix = np.eye(3)
    pitch_matrix = np.eye(3)
    
    if keys[K_LEFT] or keys[K_RIGHT]:
        rotation_dir = 1 if keys[K_RIGHT] else -1
        angle = angular_speed * rotation_dir
        
        # Create rotation matrix for yaw around PLANETARY UP (not global up)
        yaw_matrix = _rotation_matrix_from_axis_angle(camera.planetary_up, angle)
    
    if keys[K_UP] or keys[K_DOWN]:
        rotation_dir = -1 if keys[K_UP] else 1
        angle = angular_speed * rotation_dir
        pitch_matrix = _rotation_matrix_from_axis_angle(camera.planetary_right, angle)
    
    # Apply rotations in consistent order: pitch first, then yaw
    # This ensures that yawing while pitched doesn't induce unwanted roll
    combined_rotation = pitch_matrix @ yaw_matrix
    camera.manual_rotation = combined_rotation @ camera.manual_rotation
    
    # === SECTION 4: FINAL ORIENTATION ===
    # Calculate base forward vector from planetary coordinate system
    base_forward = np.cross(camera.planetary_right, camera.planetary_up)
    if np.linalg.norm(base_forward) > 0:
        base_forward = base_forward / np.linalg.norm(base_forward)
    else:
        base_forward = np.array([0, 0, 1])
    
    # Apply manual rotation to base vectors
    # CRITICAL FIX: Don't rotate planetary_up - keep it as pure vertical axis
    final_forward = camera.manual_rotation @ base_forward
    final_right = camera.manual_rotation @ camera.planetary_right
    final_up = camera.planetary_up  # Keep planetary_up unchanged!
    
    # Update camera vectors directly
    camera.forward = final_forward / np.linalg.norm(final_forward)
    camera.right = final_right / np.linalg.norm(final_right)
    camera.up = final_up / np.linalg.norm(final_up)
    
    # === SECTION 5: DISTANCE CORRECTION ===
    # Fix camera distance to planetary body
    new_anchor_vector = planetary_body.position - camera.position
    new_distance = np.linalg.norm(new_anchor_vector)
    
    if new_distance > 0:
        # Fix distance to radius + 1
        target_distance = planetary_body.radius + 1e9
        new_anchor_normalized = new_anchor_vector / new_distance
        camera.position = planetary_body.position - new_anchor_normalized * target_distance


def _rotation_matrix_from_axis_angle(axis, angle):
    """Create rotation matrix from axis and angle using Rodrigues' formula"""
    axis = axis / np.linalg.norm(axis)  # Ensure axis is normalized
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    
    # Rodrigues' rotation formula in matrix form
    # R = I*cos(θ) + (1-cos(θ))*aa^T + sin(θ)*[a]_x
    axis_outer = np.outer(axis, axis)
    axis_cross = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0]
    ])
    
    rotation_matrix = (np.eye(3) * cos_angle + 
                      axis_outer * (1 - cos_angle) + 
                      axis_cross * sin_angle)
    
    return rotation_matrix


def handle_camera_input(camera, keys, movement_speed_multiplier=1.0):
    """Handle camera control input using vector-based rotation"""
    # Rotation using vector methods
    if keys[K_LEFT]:
        camera.rotate_yaw(-0.02)  # Yaw around world up
    if keys[K_RIGHT]:
        camera.rotate_yaw(0.02)
    if keys[K_UP]:
        camera.rotate_pitch(-0.02)  # Pitch around local right
    if keys[K_DOWN]:
        camera.rotate_pitch(0.02)
    
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
