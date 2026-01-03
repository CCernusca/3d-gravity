import pygame
import numpy as np
from scripts.camera import Camera, project_3d_to_2d

# Visual constants
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Planet colors
SUN_COLOR = (255, 255, 100)
MERCURY_COLOR = (169, 169, 169)
VENUS_COLOR = (255, 165, 0)
EARTH_COLOR = (100, 150, 255)
MARS_COLOR = (255, 100, 100)
JUPITER_COLOR = (255, 200, 150)
SATURN_COLOR = (255, 220, 180)
URANUS_COLOR = (150, 200, 255)
NEPTUNE_COLOR = (50, 100, 255)
PLUTO_COLOR = (200, 180, 160)

# Screen constants
WIDTH, HEIGHT = 1000, 800


def render_scene(screen, bodies, camera, show_trails, show_ui, time_multiplier, movement_speed_multiplier, width, height):
    """Render the entire scene"""
    screen.fill(BLACK)
    
    # Draw trails
    if show_trails:
        draw_trails(screen, bodies, camera, width, height)
    
    # Draw bodies
    draw_bodies(screen, bodies, camera, width, height)
    
    # Draw UI
    if show_ui:
        draw_ui(screen, camera, show_trails, time_multiplier, movement_speed_multiplier, width, height)


def draw_trails(screen, bodies, camera, width, height):
    """Draw orbital trails for all bodies"""
    for body in bodies:
        trail_segments = []  # List of trail segments (each segment is a list of points)
        current_segment = []
        
        # Process all trail points
        for pos in body.trail:
            proj_x, proj_y, cam_z = project_3d_to_2d(pos, camera, width, height)
            
            # Check if point is behind camera or invalid
            if (not isinstance(proj_x, (int, float)) or not isinstance(proj_y, (int, float)) or 
                cam_z <= 0 or proj_x < -100 or proj_x > width + 100 or 
                proj_y < -100 or proj_y > height + 100):
                # Point is behind camera or off-screen - end current segment
                if len(current_segment) > 1:
                    trail_segments.append(current_segment)
                current_segment = []
            else:
                # Point is visible - add to current segment
                current_segment.append((int(proj_x), int(proj_y)))
        
        # Add current position
        current_proj_x, current_proj_y, current_cam_z = project_3d_to_2d(body.position, camera, width, height)
        if (isinstance(current_proj_x, (int, float)) and isinstance(current_proj_y, (int, float)) and 
            current_cam_z > 0 and -100 <= current_proj_x <= width + 100 and 
            -100 <= current_proj_y <= height + 100):
            current_segment.append((int(current_proj_x), int(current_proj_y)))
        
        # Add final segment if it has points
        if len(current_segment) > 1:
            trail_segments.append(current_segment)
        
        # Draw all trail segments
        for segment in trail_segments:
            if len(segment) > 1:
                pygame.draw.lines(screen, body.color, False, segment, 1)


def draw_bodies(screen, bodies, camera, width, height):
    """Draw all celestial bodies with proper depth sorting"""
    # Calculate depth and projection for all bodies
    body_renders = []
    for body in bodies:
        # Use camera vectors for depth calculation
        relative_pos = body.position - camera.position
        
        # Get camera axes
        right = camera.get_right_vector()
        up = camera.get_up_vector()
        forward = camera.get_forward_vector()
        
        # Transform to camera coordinates (dot products)
        cam_x = np.dot(relative_pos, right)
        cam_y = np.dot(relative_pos, up)
        cam_z = np.dot(relative_pos, forward)
        
        proj_x, proj_y, scale = project_3d_to_2d(body.position, camera, width, height)
        body_renders.append((cam_z, body, proj_x, proj_y, scale))
    
    # Sort by z-depth (furthest first)
    body_renders.sort(key=lambda x: x[0], reverse=True)
    
    # Draw bodies
    for _, body, proj_x, proj_y, scale in body_renders:
        # Skip if projection is invalid or off-screen
        if not (isinstance(proj_x, (int, float)) and isinstance(proj_y, (int, float))):
            continue
        if proj_x < -100 or proj_x > width + 100 or proj_y < -100 or proj_y > height + 100:
            continue
        
        radius = max(1.5, int(body.radius * scale))
        pygame.draw.circle(screen, body.color, (int(proj_x), int(proj_y)), radius)


def draw_ui(screen, camera, show_trails, time_multiplier, movement_speed_multiplier, width, height):
    """Draw user interface elements"""
    font = pygame.font.Font(None, 24)
    
    # Convert rotation to degrees and wrap around 360
    pitch_deg = np.degrees(camera.pitch) % 360
    yaw_deg = np.degrees(camera.yaw) % 360
    
    instructions = [
        "ESC: Exit | SPACE: Pause/Resume",
        "T: Toggle Trails | R: Reset",
        "+/-: Speed Up/Slow Down Time (0.01x - 100x)",
        "./,: Faster/Slower Movement (0.1x - 10x)",
        "Arrow Keys: Rotate View",
        "WASD: Move Camera (relative to view)",
        "Q/E: Move Forward/Backward",
        f"Trails: {'ON' if show_trails else 'OFF'}",
        f"Time: {time_multiplier:.2f}x",
        f"Move Speed: {movement_speed_multiplier:.2f}x",
        f"Position: ({camera.position[0]/1e11:.1f}, {camera.position[1]/1e11:.1f}, {camera.position[2]/1e11:.1f}) x10¹¹m",
        f"Rotation: (Pitch: {pitch_deg:.1f}°, Yaw: {yaw_deg:.1f}°)"
    ]
    
    for i, text in enumerate(instructions):
        surface = font.render(text, True, WHITE)
        screen.blit(surface, (10, 10 + i * 25))
