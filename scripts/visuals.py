import pygame
import numpy as np
from scripts.camera import Camera, project_3d_to_2d, check_hover, get_planetary_coordinates

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


def render_scene(screen, bodies, camera, show_trails, show_ui, time_multiplier, movement_speed_multiplier, width, height, locked_body=None, planetary_body=None):
    """Render the entire scene"""
    screen.fill(BLACK)
    
    # Draw trails
    if show_trails:
        draw_trails(screen, bodies, camera, width, height)
    
    # Draw bodies
    draw_bodies(screen, bodies, camera, width, height, planetary_body)
    
    # Draw hover information
    mouse_pos = pygame.mouse.get_pos()
    hovered_body = check_hover(mouse_pos, bodies, camera, width, height)
    if hovered_body:
        draw_hover_info(screen, hovered_body, camera, width, height)
    
    # Draw UI
    if show_ui:
        draw_ui(screen, camera, show_trails, show_ui, time_multiplier, movement_speed_multiplier, width, height, locked_body, planetary_body)


def draw_trails(screen, bodies, camera, width, height):
    """Draw orbital trails for all bodies"""
    for body in bodies:
        trail_segments = []  # List of trail segments (each segment is a list of points)
        current_segment = []
        
        # Process all trail points
        for pos in body.trail:
            proj_x, proj_y, cam_z, scale = project_3d_to_2d(pos, camera, width, height)
            
            # Skip if projection failed
            if proj_x is None or proj_y is None or cam_z is None or scale is None:
                # Point is behind camera or invalid - end current segment
                if len(current_segment) > 1:
                    trail_segments.append(current_segment)
                current_segment = []
                continue
            
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
        current_proj_x, current_proj_y, current_cam_z, scale = project_3d_to_2d(body.position, camera, width, height)
        
        # Skip if projection failed
        if current_proj_x is not None and current_proj_y is not None and current_cam_z is not None:
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


def draw_bodies(screen, bodies, camera, width, height, planetary_body=None):
    """Draw all celestial bodies with depth sorting"""
    body_renders = []
    
    for body in bodies:
        # In planetary mode, always render the planetary body
        if planetary_body and body == planetary_body:
                # Force planetary body to render last (on top) by using maximum depth
                body_renders.append((0, body, 0, 0, 1))  # Always on top
        else:
            # Normal rendering for other bodies
            # Transform to camera space (translate)
            relative_pos = body.position - camera.position
            
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
            
            proj_x, proj_y, _, scale = project_3d_to_2d(body.position, camera, width, height)
            
            # Skip if projection failed
            if proj_x is None or proj_y is None or scale is None:
                continue
                
            body_renders.append((cam_z, body, proj_x, proj_y, scale))
    
    # Sort by z-depth (furthest first)
    body_renders.sort(key=lambda x: x[0], reverse=True)
    
    # Draw bodies
    for _, body, proj_x, proj_y, scale in body_renders:
        # Special case for planetary body
        if planetary_body and body == planetary_body:
            # Always render planetary body with partial visibility support
            # Get projection scale first
            _, _, _, proj_scale = project_3d_to_2d(body.position, camera, width, height)
            
            if proj_scale is not None:
                # Calculate screen space radius
                screen_radius = max(3, int(body.radius * proj_scale))
                
                # Draw the filled circle if center is on screen
                center_proj_x, center_proj_y, center_cam_z, center_scale = project_3d_to_2d(body.position, camera, width, height)
                if center_proj_x is not None and center_proj_y is not None and center_cam_z is not None and center_scale is not None:
                    pygame.draw.circle(screen, body.color, (int(center_proj_x), int(center_proj_y)), screen_radius)
            # Skip normal rendering
            continue
            
        # Skip if projection is invalid or off-screen
        if not (isinstance(proj_x, (int, float)) and isinstance(proj_y, (int, float))):
            continue
        if proj_x < -100 or proj_x > width + 100 or proj_y < -100 or proj_y > height + 100:
            continue
        
        radius = max(1.5, int(body.radius * scale))
        pygame.draw.circle(screen, body.color, (int(proj_x), int(proj_y)), radius)


def draw_ui(screen, camera, show_trails, show_ui, time_multiplier, movement_speed_multiplier, width, height, locked_body=None, planetary_body=None):
    """Draw user interface elements"""
    font = pygame.font.Font(None, 24)
    
    # Get rotation angles from vectors
    yaw_deg, pitch_deg, roll_deg = camera.get_angles_for_display()
    yaw_deg = np.degrees(yaw_deg) % 360
    pitch_deg = np.degrees(pitch_deg) % 360
    roll_deg = np.degrees(roll_deg) % 360
    
    # Get planetary manual rotation info if in planetary mode
    planetary_rotation_info = ""
    if planetary_body and hasattr(camera, 'manual_rotation'):
        # Extract angles from manual rotation matrix for display
        try:
            # Convert rotation matrix to Euler angles for display
            manual_yaw = np.arctan2(camera.manual_rotation[1, 0], camera.manual_rotation[0, 0])
            manual_pitch = np.arcsin(-camera.manual_rotation[2, 0])
            manual_roll = np.arctan2(camera.manual_rotation[2, 1], camera.manual_rotation[2, 2])
            
            manual_yaw_deg = np.degrees(manual_yaw) % 360
            manual_pitch_deg = np.degrees(manual_pitch) % 360
            manual_roll_deg = np.degrees(manual_roll) % 360
            planetary_rotation_info = f"Manual: (Yaw: {manual_yaw_deg:.1f}°, Pitch: {manual_pitch_deg:.1f}°, Roll: {manual_roll_deg:.1f}°)"
        except:
            planetary_rotation_info = "Manual: (Vector-based rotation)"
    
    # Get planetary coordinates if in planetary mode
    coord_info = ""
    if planetary_body:
        latitude, longitude, altitude, distance = get_planetary_coordinates(camera, planetary_body)
        if latitude is not None:
            coord_info = f"Lat: {latitude:.2f}° | Lon: {longitude:.2f}° | Alt: {altitude/1e6:.1f}Mm"
    
    # Build instructions list
    instructions = [
        "ESC: Exit | SPACE: Pause/Resume",
        "T: Toggle Trails | R: Reset",
        "+/-: Speed Up/Slow Down Time (0.01x - 100x)",
        "./,: Faster/Slower Movement (0.1x - 10x)",
        "Arrow Keys: Rotate View",
        "WASD: Move Camera (relative to view)",
        "Q/E: Move Forward/Backward",
        "L: Lock to hovered planet",
        "P: Planetary mode (fixed distance)",
        f"Trails: {'ON' if show_trails else 'OFF'}",
        f"Time: {time_multiplier:.2f}x",
        f"Move Speed: {movement_speed_multiplier:.2f}x",
        f"Position: ({camera.position[0]/1e11:.1f}, {camera.position[1]/1e11:.1f}, {camera.position[2]/1e11:.1f}) x10¹¹m",
        f"Rotation: (Pitch: {pitch_deg:.1f}°, Yaw: {yaw_deg:.1f}°, Roll: {roll_deg:.1f}°)"
    ]
    
    # Add planetary coordinates if available
    if coord_info:
        instructions.insert(-2, f"Planetary: {coord_info}")
    
    # Add planetary manual rotation if available
    if planetary_rotation_info:
        instructions.insert(-2, planetary_rotation_info)
    
    # Add mode information
    if locked_body:
        instructions.append(f"LOCKED to: {locked_body.name}")
    elif planetary_body:
        instructions.append(f"PLANETARY mode: {planetary_body.name}")
    
    # Add planetary mode status if in planetary mode
    if planetary_body:
        planetary_info = f"PLANETARY: {planetary_body.name} (Press P to exit)"
        instructions.insert(9, planetary_info)
    
    for i, text in enumerate(instructions):
        surface = font.render(text, True, WHITE)
        screen.blit(surface, (10, 10 + i * 25))


def draw_hover_info(screen, body, camera, width, height):
    """Draw hover information for a celestial body"""
    font = pygame.font.Font(None, 20)
    
    # Get body position and project to screen
    proj_x, proj_y, cam_z, scale = project_3d_to_2d(body.position, camera, width, height)
    
    # Skip if projection failed
    if proj_x is None or proj_y is None or cam_z is None or scale is None:
        return
    
    if not (isinstance(proj_x, (int, float)) and isinstance(proj_y, (int, float))):
        return
    
    # Calculate screen radius for halo
    screen_radius = max(7, int(body.radius * scale))
    
    # Draw white halo
    pygame.draw.circle(screen, (255, 255, 255), (int(proj_x), int(proj_y)), screen_radius + 3, 2)
    
    # Prepare information text
    info_lines = [
        f"Name: {body.name}",
        f"Mass: {body.mass:.2e} kg",
        f"Radius: {body.radius/1e6:.1f} Mm",
        f"Position: ({body.position[0]/1e9:.1f}, {body.position[1]/1e9:.1f}, {body.position[2]/1e9:.1f}) Gm",
        f"Velocity: ({body.velocity[0]/1000:.1f}, {body.velocity[1]/1000:.1f}, {body.velocity[2]/1000:.1f}) km/s"
    ]
    
    # Render text background for better visibility
    text_surfaces = []
    max_text_width = 0
    
    for i, line in enumerate(info_lines):
        surface = font.render(line, True, WHITE)
        text_surfaces.append(surface)
        max_text_width = max(max_text_width, surface.get_width())
    
    # Position text above the body
    text_x = int(proj_x) - max_text_width // 2
    text_y = int(proj_y) - screen_radius - 30 - len(info_lines) * 22
    
    # Draw background rectangle
    padding = 8
    bg_rect = pygame.Rect(
        text_x - padding,
        text_y - padding,
        max_text_width + padding * 2,
        len(info_lines) * 22 + padding * 2
    )
    pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
    pygame.draw.rect(screen, WHITE, bg_rect, 1)
    
    # Draw text
    for i, surface in enumerate(text_surfaces):
        screen.blit(surface, (text_x, text_y + i * 22))
