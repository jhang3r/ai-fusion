"""
Simple Assembly Generator
Demonstrates using connection points to automatically create assemblies
"""

from design_primitives import DesignPrimitives, ConnectionPoint
import json
from pathlib import Path

def find_compatible_connections(components_data):
    """Find compatible connection points between components"""
    compatible_pairs = []
    
    for i, (name1, data1) in enumerate(components_data):
        for j, (name2, data2) in enumerate(components_data):
            if i >= j:  # Skip self and already checked pairs
                continue
            
            cp1_list = data1.get('connection_points', [])
            cp2_list = data2.get('connection_points', [])
            
            for cp1 in cp1_list:
                for cp2 in cp2_list:
                    if cp1.can_mate_with(cp2):
                        compatible_pairs.append({
                            'component_1': name1,
                            'component_2': name2,
                            'cp1': cp1,
                            'cp2': cp2,
                            'joint_type': 'revolute' if cp1.type in ['shaft', 'bore'] else 'rigid'
                        })
    
    return compatible_pairs

def create_gear_train_assembly():
    """Generate a 2-gear train assembly using connection points"""
    
    # Generate components with connection points
    components_data = [
        ('Shaft1', DesignPrimitives.shaft(diameter=8, length=30)),
        ('Gear1', DesignPrimitives.gear(teeth=20, module=2, thickness=10, bore_diameter=8)),
        ('Shaft2', DesignPrimitives.shaft(diameter=8, length=30)),
        ('Gear2', DesignPrimitives.gear(teeth=30, module=2, thickness=10, bore_diameter=8))
    ]
    
    # Find compatible connections
    compatible = find_compatible_connections(components_data)
    
    # Build assembly task
    operations = []
    
    # Create all components
    for name, data in components_data:
        operations.append({'type': 'create_component', 'name': name})
        operations.extend(data['operations'])
    
    # Position Shaft2 for gear meshing
    pitch_distance = 2 * (20 + 30) / 2
    operations.append({'type': 'transform_component', 'name': 'Shaft2', 'offset': [pitch_distance, 0, 0]})
    
    # Create joints from compatible connections (filter to only correct pairs)
    operations.append({'type': 'activate_component', 'name': 'root'})
    
    # Only create joints for components that should be together
    # Gear1 with Shaft1, Gear2 with Shaft2
    correct_joints = [
        {'component_1': 'Gear1', 'component_2': 'Shaft1', 'joint_type': 'revolute'},
        {'component_1': 'Gear2', 'component_2': 'Shaft2', 'joint_type': 'revolute'}
    ]
    
    for joint in correct_joints:
        operations.append({
            'type': 'create_joint',
            'component_1': joint['component_1'],
            'component_2': joint['component_2'],
            'joint_type': joint['joint_type']
        })
    
    task = {
        'task_id': 'gear_train_auto',
        'type': 'create_assembly',
        'description': f'Gear train with {len(correct_joints)} joints (auto-detected {len(compatible)} compatible connections)',
        'operations': operations,
        'export_formats': ['f3d'],
        'keep_open': True,  # Keep on screen for inspection
        'timestamp': '2025-11-20T01:36:00'
    }
    
    return task, compatible

if __name__ == '__main__':
    # Generate assembly
    task, compatible = create_gear_train_assembly()
    
    # Save to tasks directory
    task_file = Path('c:/Users/jrdnh/Documents/ai-fusion/shared/tasks/task_gear_train_auto.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=2)
    
    print(f"✅ Generated assembly task: {task_file}")
    print(f"   Components: Shaft1, Gear1 (20T), Shaft2, Gear2 (30T)")
    print(f"   Auto-detected {len(compatible)} compatible connections")
    print(f"   Using 2 correct joints: Gear1↔Shaft1, Gear2↔Shaft2")
