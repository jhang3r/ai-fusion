"""
Comprehensive training run with all features - Production Run
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
        'mounting_plate',  # Fixed and working!
        'bottle',
        'handle',
        'propeller',       # Fixed and working!
        'enclosure',
        'shaft',
        'ribbed_plate',
        'complex_random_part' # NEW: High complexity!
    ]
    
    print("🚀 Starting Production Fusion 360 AI Training Session")
    print(f"   Task types: {len(task_types)} different types")
    print(f"   Iterations: 100\n")
    
    # Run training
    orchestrator.run_training_session(task_types=task_types, iterations=100)
