"""
Quick training run script
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from training_orchestrator import TrainingOrchestrator

if __name__ == "__main__":
    workspace = Path(__file__).parent
    orchestrator = TrainingOrchestrator(workspace)
    
    # Define task types to train on
    task_types = [
        'simple_cylinder',
        'simple_box',
        'gear',
        'bolt',
        'bracket',
        'mounting_plate'
    ]
    
    print("🚀 Starting Fusion 360 AI Training Session")
    print(f"   Task types: {', '.join(task_types)}")
    print(f"   Iterations: 10\n")
    
    # Run training
    orchestrator.run_training_session(task_types=task_types, iterations=10)
