"""
Simple Assembly Generator
Demonstrates using connection points to automatically create assemblies
"""

from design_primitives import DesignPrimitives, ConnectionPoint
import json
from pathlib import Path

def create_gear_train_assembly():
    """Generate a 2-gear train assembly using connection points"""
    
    # Generate components with connection points
    shaft1_data = DesignPrimitives.shaft(diameter=8, length=30)
    gear1_data = DesignPrimitives.gear(teeth=20, module=2, thickness=10, bore_diameter=8)
    gear2_data = DesignPrimitives.gear(teeth=30, module=2, thickness=10, bore_diameter=8)
    shaft2_data = DesignPrimitives.shaft(diameter=8, length=30)
    
    # Build assembly task
    operations = []
    
    # Shaft 1
    operations.append({'type': 'create_component', 'name': 'Shaft1'})
    operations.extend(shaft1_data['operations'])
    
    # Gear 1 on Shaft 1
    operations.append({'type': 'create_component', 'name': 'Gear1'})
    operations.extend(gear1_data['operations'])
    
    # Shaft 2 (offset for meshing gears)
    operations.append({'type': 'create_component', 'name': 'Shaft2'})
    operations.extend(shaft2_data['operations'])
    pitch_distance = 2 * (20 + 30) / 2  # Pitch diameter calculation
    operations.append({'type': 'transform_component', 'name': 'Shaft2', 'offset': [pitch_distance, 0, 0]})
    
    # Gear 2 on Shaft 2
    operations.append({'type': 'create_component', 'name': 'Gear2'})
    operations.extend(gear2_data['operations'])
    
    # Create joints using connection points
    operations.append({'type': 'activate_component', 'name': 'root'})
    operations.append({'type': 'create_joint', 'component_1': 'Gear1', 'component_2': 'Shaft1', 'joint_type': 'revolute'})
    operations.append({'type': 'create_joint', 'component_1': 'Gear2', 'component_2': 'Shaft2', 'joint_type': 'revolute'})
    
    task = {
        'task_id': 'gear_train_auto',
        'type': 'create_assembly',
        'description': 'Auto-generated gear train from connection points',
        'operations': operations,
        'export_formats': ['f3d'],
        'timestamp': '2025-11-20T01:27:00'
    }
    
    return task

if __name__ == '__main__':
    # Generate assembly
    task = create_gear_train_assembly()
    
    # Save to tasks directory
    task_file = Path('c:/Users/jrdnh/Documents/ai-fusion/shared/tasks/task_gear_train_auto.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=2)
    
    print(f"✅ Generated assembly task: {task_file}")
    print(f"   Components: Shaft1, Gear1 (20T), Shaft2, Gear2 (30T)")
    print(f"   Joints: 2x revolute (gear-to-shaft)")
