import pygame
from pygame.locals import *
from scripts.physics import Body, update_physics, FPS, TIME_MULTIPLIER
from scripts.camera import Camera, handle_camera_input, handle_locked_camera_input, handle_planetary_input, check_hover
from scripts.visuals import render_scene, SUN_COLOR, MERCURY_COLOR, VENUS_COLOR, EARTH_COLOR, MARS_COLOR, JUPITER_COLOR, SATURN_COLOR, URANUS_COLOR, NEPTUNE_COLOR, PLUTO_COLOR
import numpy as np

# Screen dimensions
WIDTH, HEIGHT = 1000, 800


def create_solar_system():
    """Create a complete solar system with realistic orbital inclinations"""
    # Scale factor based on astronomical distances
    # Multiply radii by distance scale to make them visible
    distance_scale = 1e8  # Scale factor for visibility at astronomical distances
    
    # Orbital inclinations in radians (relative to solar system plane)
    # Mercury: 7.0°, Venus: 3.4°, Earth: 0°, Mars: 1.9°, Jupiter: 1.3°, Saturn: 2.5°, Uranus: 0.8°, Neptune: 1.8°, Pluto: 17.2°
    
    return [
        # Sun (massive for visual impact)
        Body("Sun", 1.989e30, [0, 0, 0], [0, 0, 0], 80 * distance_scale, SUN_COLOR),
        
        # Inner planets with orbital inclinations
        Body("Mercury", 3.301e23, [5.79e10, 0, 0], [0, 0, 47870], 15 * distance_scale, MERCURY_COLOR, inclination=np.radians(7.0)),
        Body("Venus", 4.867e24, [1.082e11, 0, 0], [0, 0, 35020], 25 * distance_scale, VENUS_COLOR, inclination=np.radians(3.4)),
        Body("Earth", 5.972e24, [1.496e11, 0, 0], [0, 0, 29780], 30 * distance_scale, EARTH_COLOR, inclination=np.radians(0.0)),
        Body("Mars", 6.39e23, [2.279e11, 0, 0], [0, 0, 24070], 20 * distance_scale, MARS_COLOR, inclination=np.radians(1.9)),
        
        # Gas giants with orbital inclinations
        Body("Jupiter", 1.898e27, [7.785e11, 0, 0], [0, 0, 13070], 60 * distance_scale, JUPITER_COLOR, inclination=np.radians(1.3)),
        Body("Saturn", 5.683e26, [1.434e12, 0, 0], [0, 0, 9680], 50 * distance_scale, SATURN_COLOR, inclination=np.radians(2.5)),
        
        # Ice giants with orbital inclinations
        Body("Uranus", 8.681e25, [2.873e12, 0, 0], [0, 0, 6800], 35 * distance_scale, URANUS_COLOR, inclination=np.radians(0.8)),
        Body("Neptune", 1.024e26, [4.495e12, 0, 0], [0, 0, 5430], 33 * distance_scale, NEPTUNE_COLOR, inclination=np.radians(1.8)),
        
        # Dwarf planet with highly inclined orbit
        Body("Pluto", 1.309e22, [5.906e12, 0, 0], [0, 0, 4740], 10 * distance_scale, PLUTO_COLOR, inclination=np.radians(17.2))
    ]


def main():
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("3D Gravity Simulation")
    clock = pygame.time.Clock()
    
    # Dynamic screen dimensions
    current_width, current_height = WIDTH, HEIGHT
    
    # Create celestial bodies
    bodies = create_solar_system()
    
    # Camera
    camera = Camera()
    
    # Game state
    paused = False
    show_trails = True
    show_ui = True  # Toggle for UI instructions
    time_multiplier = TIME_MULTIPLIER
    movement_speed_multiplier = 1.0  # For adjustable camera movement speed
    locked_body = None  # Camera lock target
    planetary_body = None  # Planetary mode target
    running = True
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == VIDEORESIZE:
                # Handle window resize
                old_width, old_height = current_width, current_height
                current_width, current_height = event.w, event.h
                screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    paused = not paused
                elif event.key == K_t:
                    show_trails = not show_trails
                elif event.key == K_c:
                    show_ui = not show_ui
                elif event.key == K_l:
                    # Lock camera to hovered body or unlock
                    hovered_body = check_hover(pygame.mouse.get_pos(), bodies, camera, current_width, current_height)
                    locked_body = hovered_body if hovered_body else None
                    # Clear planetary mode when locking
                    planetary_body = None
                elif event.key == K_p:
                    # Planetary mode: fix distance to hovered body
                    hovered_body = check_hover(pygame.mouse.get_pos(), bodies, camera, current_width, current_height)
                    planetary_body = hovered_body if hovered_body else None
                    # Clear lock mode when entering planetary mode
                    locked_body = None
                    # Clear planetary attributes
                    for attr in ['planetary_initial_forward', 'planetary_initial_anchor', 'planetary_initial_pitch', 'planetary_initial_yaw']:
                        if hasattr(camera, attr):
                            delattr(camera, attr)
                    if not locked_body and planetary_body:
                        # CRITICAL FIX: Position camera at north pole and set up orientation
                        # North pole is at body.position + (0, radius + offset, 0) in world coordinates
                        north_pole_offset = np.array([0.0, planetary_body.radius + 7e7, 0.0])
                        camera.position = planetary_body.position + north_pole_offset
                        
                        # Set camera orientation directly for north pole view
                        # At north pole: up points away from planet, forward points down, right points east
                        planetary_up_vector = np.array([0.0, 1.0, 0.0])  # Up at north pole (world Y)
                        camera.up = planetary_up_vector / np.linalg.norm(planetary_up_vector)  # Normalize
                        camera.forward = -planetary_up_vector  # Look down toward planet center
                        camera.forward = camera.forward / np.linalg.norm(camera.forward)  # Normalize
                        
                        # Calculate right vector to maintain orthogonal system (cross product order: up × forward)
                        camera.right = np.cross(camera.up, camera.forward)
                        if np.linalg.norm(camera.right) > 1e-6:
                            camera.right = camera.right / np.linalg.norm(camera.right)
                        else:
                            # Fallback if cross product fails
                            camera.right = np.array([1.0, 0.0, 0.0])
                        
                        # Initialize planetary coordinate system
                        # planetary_up should point away from planet center (surface normal)
                        radial_vector = camera.position - planetary_body.position
                        if np.linalg.norm(radial_vector) > 0:
                            camera.planetary_up = radial_vector / np.linalg.norm(radial_vector)
                        else:
                            camera.planetary_up = np.array([0.0, 1.0, 0.0])
                        
                        # planetary_right should be stable (east-west direction)
                        # At north pole, east is along world X axis
                        camera.planetary_right = np.array([1.0, 0.0, 0.0])
                        
                        # Clear any existing manual rotation
                        if hasattr(camera, 'manual_rotation'):
                            camera.manual_rotation = np.eye(3)
                        else:
                            camera.manual_rotation = np.eye(3)
                elif event.key == K_r:
                    # Reset simulation
                    bodies = create_solar_system()
                    time_multiplier = TIME_MULTIPLIER
                    movement_speed_multiplier = 1.0
                elif event.key == K_PLUS or event.key == K_EQUALS:
                    # Speed up time
                    time_multiplier = min(time_multiplier * 2, 100.0)
                elif event.key == K_MINUS:
                    # Slow down time
                    time_multiplier = max(time_multiplier / 1.5, 0.01)
                elif event.key == K_PERIOD:
                    # Faster movement speed
                    movement_speed_multiplier = min(movement_speed_multiplier * 1.5, 10.0)
                elif event.key == K_COMMA:
                    # Slower movement speed
                    movement_speed_multiplier = max(movement_speed_multiplier / 1.5, 0.1)
        
        # Handle continuous input
        keys = pygame.key.get_pressed()
        if locked_body:
            # When locked, only allow orbital movement (WASD) and zoom (QE)
            handle_locked_camera_input(camera, keys, movement_speed_multiplier, locked_body)
        elif planetary_body:
            # Planetary mode: normal rotation + perpendicular movement
            handle_planetary_input(camera, keys, movement_speed_multiplier, planetary_body)
        else:
            # Normal camera controls when not locked
            handle_camera_input(camera, keys, movement_speed_multiplier)
        
        # Update physics
        if not paused:
            # Store planetary body position before physics update
            if planetary_body:
                old_planetary_position = planetary_body.position.copy()
            
            update_physics(bodies, time_multiplier)
            
            # Apply planetary body movement to camera
            if planetary_body:
                planetary_movement = planetary_body.position - old_planetary_position
                camera.position += planetary_movement
        
        # Update camera lock
        if locked_body:
            # Calculate camera movement to follow locked body
            if not hasattr(camera, 'lock_offset'):
                # Initialize lock offset when first locking
                camera.lock_offset = camera.position - locked_body.position
            
            # Move camera with locked body
            camera.position = locked_body.position + camera.lock_offset
        elif planetary_body:
            # Planetary mode: handle movement in handle_planetary_input
            # Don't override camera position here - let handle_planetary_input manage it
            pass
        else:
            # Clear lock offset when not locked
            if hasattr(camera, 'lock_offset'):
                delattr(camera, 'lock_offset')
        
        # Render
        render_scene(screen, bodies, camera, show_trails, show_ui, time_multiplier, movement_speed_multiplier, current_width, current_height, locked_body, planetary_body)
        
        # Update display
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()


if __name__ == "__main__":
    main()