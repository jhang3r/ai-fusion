"""
Design Primitives Library
Reusable design operation templates for common mechanical components.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
import random


@dataclass
class ConnectionPoint:
    """Represents a semantic connection point on a component"""
    type: str  # 'threaded_hole', 'shaft', 'bore', 'mounting_pattern', 'flat_face'
    position: List[float]  # [x, y, z] in mm
    properties: Dict[str, Any] = field(default_factory=dict)
    component_id: str = None
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = f"{self.type}_{random.randint(1000, 9999)}"
    
    def can_mate_with(self, other: 'ConnectionPoint') -> bool:
        """Check if this connection point can mate with another"""
        mates = {
            'threaded_hole': ['bolt', 'screw'],
            'bolt': ['threaded_hole', 'clearance_hole'],
            'shaft': ['bore', 'bearing'],
            'bore': ['shaft'],
            'mounting_pattern': ['mounting_pattern'],
            'flat_face': ['flat_face']
        }
        return other.type in mates.get(self.type, [])


class DesignPrimitives:
    """Library of common design operations and components"""
    
    @staticmethod
    def cylinder(diameter: float, height: float, center: List[float] = None) -> List[Dict]:
        """Generate operations for a simple cylinder"""
        if center is None:
            center = [0, 0]
        
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': diameter / 2,
                    'center': center
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': height
            }
        ]
    
    @staticmethod
    def box(width: float, depth: float, height: float) -> List[Dict]:
        """Generate operations for a rectangular box"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'rectangle',
                'params': {
                    'width': width,
                    'height': depth
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': height
            }
        ]
    
    @staticmethod
    def sphere(diameter: float) -> List[Dict]:
        """Generate operations for a sphere"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': diameter / 2,
                    'center': [0, 0]
                }
            },
            {
                'type': 'revolve',
                'profile': 'sketch_1',
                'axis': 'Y',
                'angle': 360
            }
        ]
    
    @staticmethod
    def gear(teeth: int, module: float, thickness: float, bore_diameter: float = 0) -> List[Dict]:
        """Generate operations for a spur gear"""
        operations = [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'gear_profile',
                'params': {
                    'teeth': teeth,
                    'module': module
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': thickness
            }
        ]
        
        if bore_diameter > 0:
            operations.append({
                'type': 'hole',
                'center': [0, 0],
                'diameter': bore_diameter,
                'depth': 'through'
            })
        
        return operations
    
    @staticmethod
    def hex_bolt(head_width: float, head_height: float, 
                 shaft_diameter: float, shaft_length: float) -> List[Dict]:
        """Generate operations for a hexagonal bolt"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'hexagon',
                'params': {
                    'width': head_width,
                    'center': [0, 0]
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': head_height
            },
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': shaft_diameter / 2,
                    'center': [0, 0]
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_2',
                'distance': shaft_length
            }
        ]
    
    @staticmethod
    def threaded_rod(diameter: float, length: float, pitch: float) -> List[Dict]:
        """Generate operations for a threaded rod"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': diameter / 2,
                    'center': [0, 0]
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': length
            },
            {
                'type': 'thread',
                'face': 'cylindrical',
                'pitch': pitch,
                'direction': 'right_hand'
            }
        ]
    
    @staticmethod
    def bearing_housing(outer_diameter: float, inner_diameter: float, 
                       thickness: float, flange_diameter: float = None) -> List[Dict]:
        """Generate operations for a bearing housing"""
        operations = [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': outer_diameter / 2,
                    'center': [0, 0]
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': thickness
            },
            {
                'type': 'hole',
                'center': [0, 0],
                'diameter': inner_diameter,
                'depth': 'through'
            }
        ]
        
        if flange_diameter:
            operations.extend([
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'circle',
                    'params': {
                        'radius': flange_diameter / 2,
                        'center': [0, 0]
                    }
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_2',
                    'distance': thickness * 0.3
                }
            ])
        
        return operations
    
    @staticmethod
    def scifi_panel_basic(width: float, height: float, thickness: float,
                         inset_depth: float = 1.0) -> List[Dict]:
        """Generate operations for a basic sci-fi panel with inset details"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'rectangle',
                'params': {
                    'width': width,
                    'height': height
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': thickness
            },
            {
                'type': 'sketch',
                'plane': 'top_face',
                'geometry': 'rectangle',
                'params': {
                    'width': width * 0.8,
                    'height': height * 0.8
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_2',
                'distance': -inset_depth,
                'operation': 'cut'
            }
        ]
    
    @staticmethod
    def scifi_vent(width: float, height: float, thickness: float,
                   slat_count: int = 5, slat_angle: float = 45) -> List[Dict]:
        """Generate operations for a sci-fi vent with angled slats"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'rectangle',
                'params': {
                    'width': width,
                    'height': height
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': thickness
            },
            {
                'type': 'pattern',
                'pattern_type': 'linear',
                'feature': 'slat_cut',
                'count': slat_count,
                'spacing': height / (slat_count + 1)
            }
        ]
    
    @staticmethod
    def weapon_grip(length: float, diameter: float, 
                   grip_pattern: str = 'knurled') -> List[Dict]:
        """Generate operations for a weapon grip"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {
                    'radius': diameter / 2,
                    'center': [0, 0]
                }
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': length
            },
            {
                'type': 'texture',
                'surface': 'cylindrical',
                'pattern': grip_pattern,
                'depth': 0.5
            }
        ]


    @staticmethod
    def scifi_bulkhead(width: float, height: float, thickness: float, 
                      detail_scale: float = 1.0) -> List[Dict]:
        """Generate operations for a sci-fi bulkhead with structural details"""
        return [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'multi',
                'items': [
                    # Main frame
                    {
                        'type': 'rectangle',
                        'params': {'width': width, 'height': height, 'center': [0, 0]}
                    },
                    # Corner cutouts (chamfer-like)
                    {
                        'type': 'line',
                        'params': {'start': [-width/2, -height/2 + 10*detail_scale], 'end': [-width/2 + 10*detail_scale, -height/2]}
                    },
                    {
                        'type': 'line',
                        'params': {'start': [width/2, -height/2 + 10*detail_scale], 'end': [width/2 - 10*detail_scale, -height/2]}
                    },
                    {
                        'type': 'line',
                        'params': {'start': [-width/2, height/2 - 10*detail_scale], 'end': [-width/2 + 10*detail_scale, height/2]}
                    },
                    {
                        'type': 'line',
                        'params': {'start': [width/2, height/2 - 10*detail_scale], 'end': [width/2 - 10*detail_scale, height/2]}
                    }
                ]
            },
            {
                'type': 'extrude',
                'distance': thickness
            },
            {
                'type': 'sketch',
                'plane': 'XY',
                'offset': thickness,
                'geometry': 'multi',
                'items': [
                    # Central port
                    {
                        'type': 'circle',
                        'params': {'radius': min(width, height) * 0.25, 'center': [0, 0]}
                    },
                    # Structural ribs
                    {
                        'type': 'rectangle',
                        'params': {'width': width * 0.8, 'height': height * 0.1, 'center': [0, height * 0.25]}
                    },
                    {
                        'type': 'rectangle',
                        'params': {'width': width * 0.8, 'height': height * 0.1, 'center': [0, -height * 0.25]}
                    }
                ]
            },
            {
                'type': 'extrude',
                'distance': thickness * 0.5,
                'operation': 'join'
            },
            {
                'type': 'chamfer',
                'edges': 'all',
                'distance': 0.5 * detail_scale
            }
        ]


# Example usage and templates
COMPONENT_TEMPLATES = {
    'simple_cylinder': {
        'description': 'Basic cylinder',
        'generator': DesignPrimitives.cylinder,
        'default_params': {'diameter': 20, 'height': 30}
    },
    'simple_box': {
        'description': 'Basic rectangular box',
        'generator': DesignPrimitives.box,
        'default_params': {'width': 30, 'depth': 20, 'height': 15}
    },
    'sphere': {
        'description': 'Basic sphere',
        'generator': DesignPrimitives.sphere,
        'default_params': {'diameter': 25}
    },
    'gear': {
        'description': 'Spur gear',
        'generator': DesignPrimitives.gear,
        'default_params': {'teeth': 20, 'module': 2.0, 'thickness': 10, 'bore_diameter': 8}
    },
    'hex_bolt': {
        'description': 'Hexagonal bolt',
        'generator': DesignPrimitives.hex_bolt,
        'default_params': {'head_width': 15, 'head_height': 7, 'shaft_diameter': 8, 'shaft_length': 40}
    },
    'scifi_panel': {
        'description': 'Sci-fi panel with inset',
        'generator': DesignPrimitives.scifi_panel_basic,
        'default_params': {'width': 100, 'height': 80, 'thickness': 5, 'inset_depth': 1.5}
    },
    'scifi_bulkhead': {
        'description': 'Structural sci-fi bulkhead',
        'generator': DesignPrimitives.scifi_bulkhead,
        'default_params': {'width': 100, 'height': 80, 'thickness': 10, 'detail_scale': 1.0}
    }
}


if __name__ == '__main__':
    # Example: Generate operations for a gear
    gear_ops = DesignPrimitives.gear(teeth=24, module=2.5, thickness=12, bore_diameter=10)
    
    print("Gear Operations:")
    for i, op in enumerate(gear_ops, 1):
        print(f"{i}. {op['type']}: {op.get('params', {})}")
