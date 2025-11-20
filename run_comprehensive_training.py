"""
Comprehensive training run with all features
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from training_orchestrator import TrainingOrchestrator

if __name__ == "__main__":
    workspace = Path(__file__).parent
    orchestrator = TrainingOrchestrator(workspace)
    
    # All available task types
    task_types = [
        'simple_cylinder',
        'simple_box',
        'gear',
        'bolt',
        'bracket',
        'mounting_plate',  # Now with working holes!
        'bottle',
        'handle',
        'propeller',
        'enclosure',
        'shaft',
        'ribbed_plate'
    ]
    
    print("🚀 Starting Comprehensive Fusion 360 AI Training Session")
    print(f"   Task types: {len(task_types)} different types")
    print(f"   Iterations: 20\n")
    
    # Run training
    orchestrator.run_training_session(task_types=task_types, iterations=20)
