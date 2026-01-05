import json
import numpy as np
from scripts.physics import Body
from scripts.visuals import SUN_COLOR, MERCURY_COLOR, VENUS_COLOR, EARTH_COLOR, MARS_COLOR, JUPITER_COLOR, SATURN_COLOR, URANUS_COLOR, NEPTUNE_COLOR, PLUTO_COLOR

# Color mapping for predefined bodies
COLOR_MAP = {
    "Sun": SUN_COLOR,
    "Mercury": MERCURY_COLOR,
    "Venus": VENUS_COLOR,
    "Earth": EARTH_COLOR,
    "Mars": MARS_COLOR,
    "Jupiter": JUPITER_COLOR,
    "Saturn": SATURN_COLOR,
    "Uranus": URANUS_COLOR,
    "Neptune": NEPTUNE_COLOR,
    "Pluto": PLUTO_COLOR
}

def parse_color(color_data):
    """Parse color from JSON data (hex string, rgb array, or color name)"""
    if isinstance(color_data, str):
        # Hex color
        if color_data.startswith("#"):
            hex_color = color_data.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Named color
        elif color_data in COLOR_MAP:
            return COLOR_MAP[color_data]
        else:
            raise ValueError(f"Unknown color name: {color_data}")
    elif isinstance(color_data, list) and len(color_data) == 3:
        # RGB array
        return tuple(int(c) for c in color_data)
    else:
        raise ValueError(f"Invalid color format: {color_data}")

def load_solar_system(file_path="system.json"):
    """Load solar system configuration from JSON file"""
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        bodies = []
        
        # Global settings
        distance_scale = config.get("distance_scale", 1e8)
        default_color = config.get("default_color", [255, 255, 255])
        
        # Load bodies
        for body_data in config.get("bodies", []):
            # Required fields
            name = body_data["name"]
            mass = body_data["mass"]
            position = np.array(body_data["position"])
            velocity = np.array(body_data["velocity"])
            radius = body_data.get("radius", 10) * distance_scale
            
            # Color (with fallback)
            color_data = body_data.get("color", default_color)
            try:
                color = parse_color(color_data)
            except ValueError:
                print(f"Warning: Invalid color for {name}, using default")
                color = parse_color(default_color)
            
            # Optional inclination
            inclination = body_data.get("inclination", 0)
            if isinstance(inclination, (int, float)):
                inclination = np.radians(inclination)
            
            # Create body
            body = Body(name, mass, position, velocity, radius, color, inclination)
            bodies.append(body)
        
        print(f"Loaded {len(bodies)} bodies from {file_path}")
        return bodies
        
    except FileNotFoundError:
        print(f"Warning: {file_path} not found, using default solar system")
        return create_default_solar_system()
    except json.JSONDecodeError as e:
        print(f"Error parsing {file_path}: {e}")
        return create_default_solar_system()
    except KeyError as e:
        print(f"Missing required field in {file_path}: {e}")
        return create_default_solar_system()
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return create_default_solar_system()

def create_default_solar_system():
    """Create the default solar system as fallback"""
    distance_scale = 1e8
    
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

def save_solar_system(bodies, file_path="system.json"):
    """Save current solar system configuration to JSON file"""
    config = {
        "distance_scale": 1e8,
        "default_color": [255, 255, 255],
        "bodies": []
    }
    
    for body in bodies:
        body_data = {
            "name": body.name,
            "mass": body.mass,
            "position": body.position.tolist(),
            "velocity": body.velocity.tolist(),
            "radius": body.radius / 1e8,  # Convert back from distance scale
            "color": list(body.color),
            "inclination": np.degrees(body.inclination) if hasattr(body, 'inclination') else 0
        }
        config["bodies"].append(body_data)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Saved {len(bodies)} bodies to {file_path}")
    except Exception as e:
        print(f"Error saving to {file_path}: {e}")
