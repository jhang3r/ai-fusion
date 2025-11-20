"""
Training Orchestrator for Fusion 360 AI Training System
Manages the training loop, generates tasks, analyzes results, and tracks progress.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import random
import ast

from feedback_analyzer import analyze_model


def validate_code_integrity(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate Python code for syntax errors and basic structural issues.
    Returns (is_valid, error_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check for syntax errors
        compile(code, str(file_path), 'exec')
        
        # Parse AST for structural validation
        tree = ast.parse(code)
        
        # Check for duplicate class definitions
        class_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in class_names:
                    return False, f"Duplicate class definition: {node.name}"
                class_names.append(node.name)
        
        return True, None
        
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


class LogStreamer:
    """Streams Fusion 360 logs to terminal in real-time"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.running = False
        self.thread = None
        self.logs = []
        
        # Ensure log file exists and is empty
        if log_file.exists():
            log_file.unlink()
        log_file.touch()
    
    def start(self):
        """Start streaming logs in background thread"""
        import threading
        self.running = True
        self.thread = threading.Thread(target=self._stream_logs, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop streaming logs"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _stream_logs(self):
        """Background thread that tails the log file"""
        import time
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            # Start at end of file
            f.seek(0, 2)
            
            while self.running:
                line = f.readline()
                if line:
                    try:
                        log_entry = json.loads(line.strip())
                        self.logs.append(log_entry)
                        self._print_log(log_entry)
                    except:
                        pass
                else:
                    time.sleep(0.1)
    
    def _print_log(self, log_entry: dict):
        """Print a single log entry with color coding"""
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        operation = log_entry.get('operation', '')
        timestamp = log_entry.get('timestamp', '')
        
        # Extract time only (HH:MM:SS)
        time_str = timestamp.split('T')[1][:8] if 'T' in timestamp else ''
        
        # Color code by level
        if level == 'DEBUG':
            color = Colors.GRAY
            icon = '🔵'
        elif level == 'INFO':
            color = Colors.WHITE
            icon = 'ℹ️'
        elif level == 'WARNING':
            color = Colors.YELLOW
            icon = '⚠️'
        elif level == 'ERROR':
            color = Colors.RED
            icon = '❌'
        elif level == 'CRITICAL':
            color = Colors.BOLD + Colors.RED
            icon = '🚨'
        else:
            color = Colors.WHITE
            icon = '  '
        
        # Format: [TIME] ICON MESSAGE (operation)
        op_str = f" ({operation})" if operation else ""
        print(f"{Colors.GRAY}[{time_str}]{Colors.RESET} {icon} {color}{message}{Colors.RESET}{Colors.GRAY}{op_str}{Colors.RESET}")
    
    def print_summary(self):
        """Print execution summary"""
        if not self.logs:
            return
        
        error_count = sum(1 for log in self.logs if log.get('level') == 'ERROR')
        warning_count = sum(1 for log in self.logs if log.get('level') == 'WARNING')
        
        print(f"\n{Colors.BOLD}{'━' * 70}{Colors.RESET}")
        print(f"{Colors.BOLD}EXECUTION SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'━' * 70}{Colors.RESET}")
        print(f"  Total logs: {len(self.logs)}")
        print(f"  {Colors.RED}Errors: {error_count}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Warnings: {warning_count}{Colors.RESET}")
        print(f"{Colors.BOLD}{'━' * 70}{Colors.RESET}\n")



class TrainingOrchestrator:
    """Main training loop coordinator"""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.shared_dir = workspace_dir / "shared"
        self.tasks_dir = self.shared_dir / "tasks"
        self.results_dir = self.shared_dir / "results"
        self.exports_dir = self.shared_dir / "exports"
        self.training_data_dir = workspace_dir / "training_data"
        self.sessions_dir = self.training_data_dir / "sessions"
        self.curriculum_dir = workspace_dir / "curriculum"
        
        # Ensure directories exist
        for directory in [self.shared_dir, self.tasks_dir, self.results_dir, 
                         self.exports_dir, self.training_data_dir, 
                         self.sessions_dir, self.curriculum_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.sessions_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        self.task_counter = 0
        self.current_level = 1
        self.progress = self.load_progress()
        self.learning_memory = self.load_learning_memory()
        
    def load_learning_memory(self) -> Dict:
        """Load learning memory from previous sessions"""
        memory_file = self.workspace_dir / "learning_memory.json"
        
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                return json.load(f)
        
        return {
            'lessons_learned': [],
            'parameter_adjustments': {
                'chamfer_scale_factor': 1.0,
                'variety_boost': 0.0
            },
            'task_preferences': {
                'simple_cylinder': 1.0,
                'simple_box': 1.0,
                'gear': 1.0,
                'bracket': 1.0,
                'mounting_plate': 1.0
            },
            'common_issues': {},
            'last_updated': ''
        }
    
    def save_learning_memory(self):
        """Save learning memory for future sessions"""
        memory_file = self.workspace_dir / "learning_memory.json"
        self.learning_memory['last_updated'] = datetime.now().isoformat()
        
        with open(memory_file, 'w') as f:
            json.dump(self.learning_memory, f, indent=2)
        
    def load_progress(self) -> Dict:
        """Load overall training progress"""
        progress_file = self.training_data_dir / "progress.json"
        
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                return json.load(f)
        
        return {
            'current_level': 1,
            'completed_tasks': 0,
            'total_score': 0.0,
            'best_scores': {},
            'session_history': []
        }
    
    def save_progress(self):
        """Save overall training progress"""
        progress_file = self.training_data_dir / "progress.json"
        
        with open(progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def generate_task(self, task_type: str, difficulty: int = 1) -> Dict:
        """Generate a training task based on type and difficulty"""
        self.task_counter += 1
        task_id = f"task_{self.session_id}_{self.task_counter:04d}"
        
        if task_type == "simple_cylinder":
            return self._generate_cylinder_task(task_id, difficulty)
        elif task_type == "simple_box":
            return self._generate_box_task(task_id, difficulty)
        elif task_type == "gear":
            return self._generate_gear_task(task_id, difficulty)
        elif task_type == "bolt":
            return self._generate_bolt_task(task_id, difficulty)
        elif task_type == "scifi_panel":
            return self._generate_scifi_panel_task(task_id, difficulty)
        elif task_type == "bracket":
            return self._generate_bracket_task(task_id, difficulty)
        elif task_type == "mounting_plate":
            return self._generate_mounting_plate_task(task_id, difficulty)
        elif task_type == "bottle":
            return self._generate_bottle_task(task_id, difficulty)
        elif task_type == "handle":
            return self._generate_handle_task(task_id, difficulty)
        elif task_type == "propeller":
            return self._generate_propeller_task(task_id, difficulty)
        elif task_type == "enclosure":
            return self._generate_enclosure_task(task_id, difficulty)
        elif task_type == "shaft":
            return self._generate_shaft_task(task_id, difficulty)
        elif task_type == "ribbed_plate":
            return self._generate_ribbed_plate_task(task_id, difficulty)
        elif task_type == "scifi_bulkhead":
            return self._generate_scifi_bulkhead_task(task_id, difficulty)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _generate_scifi_bulkhead_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a sci-fi bulkhead creation task"""
        width = random.uniform(80, 150) if difficulty > 1 else 100.0
        height = random.uniform(60, 120) if difficulty > 1 else 80.0
        thickness = random.uniform(5, 15) if difficulty > 1 else 10.0
        detail_scale = random.uniform(0.8, 1.5) if difficulty > 1 else 1.0
        
        # Use the primitive generator to get operations
        # We need to import DesignPrimitives here or duplicate logic
        # For now, we'll duplicate the logic to keep orchestrator independent
        # but in a real system we should share the generator
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a sci-fi bulkhead {width:.1f}x{height:.1f}mm',
            'parameters': {
                'width': width,
                'height': height,
                'thickness': thickness,
                'detail_scale': detail_scale
            },
            'operations': [
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
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': width,
                'y': height,
                'z': thickness * 1.5
            },
            'timestamp': datetime.now().isoformat()
        }
        """Generate a cylinder creation task"""
        diameter = random.uniform(10, 50) if difficulty > 1 else random.uniform(15, 30)
        height = random.uniform(10, 100) if difficulty > 1 else random.uniform(20, 50)
        
        operations = [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {'radius': diameter / 2, 'center': [0, 0]}
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': height
            }
        ]
        
        # Add chamfer to all edges
        operations.append({
            'type': 'chamfer',
            'edges': 'all',
            'distance': 1.0
        })
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a cylinder with diameter {diameter:.1f}mm and height {height:.1f}mm',
            'parameters': {
                'diameter': diameter,
                'height': height
            },
            'operations': operations,
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': diameter,
                'y': diameter,
                'z': height
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_box_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a box creation task"""
        width = random.uniform(15, 60) if difficulty > 1 else random.uniform(20, 40)
        depth = random.uniform(15, 60) if difficulty > 1 else random.uniform(15, 35)
        height = random.uniform(8, 50) if difficulty > 1 else random.uniform(10, 25)
        
        operations = [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'rectangle',
                'params': {'width': width, 'height': depth}
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': height
            }
        ]
        
        # Add chamfer to all edges (proportional to smallest dimension)
        chamfer_size = min(0.5, min(width, depth, height) * 0.03)  # 3% of smallest dimension
        operations.append({
            'type': 'chamfer',
            'edges': 'all',
            'distance': chamfer_size
        })
            
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a box {width:.1f}mm × {depth:.1f}mm × {height:.1f}mm',
            'parameters': {
                'width': width,
                'depth': depth,
                'height': height
            },
            'operations': operations,
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': width,
                'y': depth,
                'z': height
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_gear_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a gear creation task"""
        teeth = random.randint(12, 40) if difficulty > 1 else random.randint(16, 24)
        module = random.uniform(1.5, 3.5) if difficulty > 1 else random.uniform(1.8, 2.5)
        thickness = random.uniform(6, 18) if difficulty > 1 else random.uniform(8, 14)
        bore = random.uniform(4, 14) if difficulty > 1 else random.uniform(6, 10)
        
        pitch_diameter = module * teeth
        outer_diameter = pitch_diameter + (2 * module)
        
        operations = [
            {
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'gear_profile',
                'params': {'teeth': teeth, 'module': module, 'bore': bore}
            },
            {
                'type': 'extrude',
                'profile': 'sketch_1',
                'distance': thickness
            }
        ]
        
        # Add finishing touches (chamfer is common on gears)
        chamfer_size = min(0.3, thickness * 0.03)  # 3% of thickness, max 0.3mm
        operations.append({
            'type': 'chamfer',
            'edges': 'all',
            'distance': chamfer_size
        })
            
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a gear with {teeth} teeth, module {module:.1f}, thickness {thickness:.1f}mm',
            'parameters': {
                'teeth': teeth,
                'module': module,
                'thickness': thickness,
                'bore_diameter': bore
            },
            'operations': operations,
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': outer_diameter,
                'y': outer_diameter,
                'z': thickness
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_bolt_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a bolt creation task"""
        head_diameter = random.uniform(10, 20) if difficulty > 1 else 15.0
        head_height = random.uniform(5, 10) if difficulty > 1 else 7.0
        shaft_diameter = random.uniform(5, 12) if difficulty > 1 else 8.0
        shaft_length = random.uniform(20, 60) if difficulty > 1 else 40.0
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a bolt with head Ø{head_diameter:.1f}mm, shaft Ø{shaft_diameter:.1f}mm × {shaft_length:.1f}mm',
            'parameters': {
                'head_diameter': head_diameter,
                'head_height': head_height,
                'shaft_diameter': shaft_diameter,
                'shaft_length': shaft_length
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'circle',
                    'params': {'radius': head_diameter / 2, 'center': [0, 0]}
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
                    'params': {'radius': shaft_diameter / 2, 'center': [0, 0]}
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_2',
                    'distance': shaft_length
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': head_diameter,
                'y': head_diameter,
                'z': head_height + shaft_length
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_scifi_panel_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a sci-fi panel creation task (more complex)"""
        width = random.uniform(50, 150) if difficulty > 1 else 100.0
        height = random.uniform(50, 150) if difficulty > 1 else 80.0
        thickness = random.uniform(2, 8) if difficulty > 1 else 5.0
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a sci-fi panel {width:.1f}mm × {height:.1f}mm × {thickness:.1f}mm with details',
            'parameters': {
                'width': width,
                'height': height,
                'thickness': thickness
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'rectangle',
                    'params': {'width': width, 'height': height}
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_1',
                    'distance': thickness
                }
                # TODO: Add more complex operations for details
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': width,
                'y': height,
                'z': thickness
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_bracket_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate an L-bracket creation task"""
        length = random.uniform(40, 90) if difficulty > 1 else random.uniform(45, 65)
        height = random.uniform(30, 80) if difficulty > 1 else random.uniform(35, 55)
        width = random.uniform(25, 70) if difficulty > 1 else random.uniform(30, 50)
        thickness = random.uniform(6, 16) if difficulty > 1 else random.uniform(8, 13)
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create an L-bracket {length:.1f}x{width:.1f}x{height:.1f}mm with {thickness:.1f}mm thickness',
            'parameters': {
                'length': length,
                'width': width,
                'height': height,
                'thickness': thickness
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'l_shape',
                    'params': {
                        'length': length, 
                        'height': height, 
                        'thickness': thickness,
                        'width': width
                    }
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_1',
                    'distance': width
                },
                {
                    'type': 'chamfer',
                    'edges': 'all',
                    'distance': min(0.5, thickness * 0.05)  # 5% of thickness
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': length,
                'y': width,
                'z': height
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_mounting_plate_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a mounting plate with 4 holes using multi-geometry sketch"""
        length = random.uniform(60, 120) if difficulty > 1 else random.uniform(70, 100)
        width = random.uniform(40, 90) if difficulty > 1 else random.uniform(50, 75)
        thickness = random.uniform(5, 14) if difficulty > 1 else random.uniform(6, 10)
        hole_diameter = random.uniform(4, 10) if difficulty > 1 else random.uniform(5, 8)
        
        # Calculate hole positions (15% from edges)
        hole_offset_x = length * 0.15
        hole_offset_y = width * 0.15
        hole_radius = hole_diameter / 2
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a mounting plate {length:.1f}x{width:.1f}x{thickness:.1f}mm with 4 holes',
            'parameters': {
                'length': length,
                'width': width,
                'thickness': thickness,
                'hole_diameter': hole_diameter
            },
            'operations': [
                # Create base plate
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'rectangle',
                    'params': {'width': length, 'height': width, 'center': [0, 0]}
                },
                {
                    'type': 'extrude',
                    'distance': thickness
                },
                # Create all 4 holes in one sketch using multi-geometry
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'offset': thickness,
                    'geometry': 'multi',
                    'items': [
                        {'type': 'circle', 'params': {'radius': hole_radius, 'center': [hole_offset_x - length/2, hole_offset_y - width/2]}},
                        {'type': 'circle', 'params': {'radius': hole_radius, 'center': [length/2 - hole_offset_x, hole_offset_y - width/2]}},
                        {'type': 'circle', 'params': {'radius': hole_radius, 'center': [hole_offset_x - length/2, width/2 - hole_offset_y]}},
                        {'type': 'circle', 'params': {'radius': hole_radius, 'center': [length/2 - hole_offset_x, width/2 - hole_offset_y]}}
                    ]
                },
                # Cut all 4 holes at once
                {
                    'type': 'extrude',
                    'distance': -(thickness + 5),
                    'operation': 'cut'
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': length,
                'y': width,
                'z': thickness
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_bottle_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a bottle creation task using revolve"""
        height = random.uniform(80, 150) if difficulty > 1 else random.uniform(90, 120)
        base_radius = random.uniform(20, 40) if difficulty > 1 else random.uniform(25, 35)
        neck_radius = random.uniform(8, 15) if difficulty > 1 else random.uniform(10, 12)
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a bottle H{height:.1f}mm x R{base_radius:.1f}mm',
            'parameters': {
                'height': height,
                'base_radius': base_radius,
                'neck_radius': neck_radius
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XZ',
                    'geometry': 'bottle_profile',
                    'params': {
                        'height': height,
                        'base_radius': base_radius,
                        'neck_radius': neck_radius
                    }
                },
                {
                    'type': 'revolve',
                    'profile': 'sketch_1',
                    'axis': 'Y',
                    'angle': 360
                },
                {
                    'type': 'chamfer',
                    'edges': 'all',
                    'distance': 0.5
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': base_radius * 2,
                'y': height,
                'z': base_radius * 2
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_handle_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a handle creation task using sweep along U-shape"""
        width = random.uniform(60, 100) if difficulty > 1 else 80.0
        height = random.uniform(30, 50) if difficulty > 1 else 40.0
        profile_radius = random.uniform(4, 8) if difficulty > 1 else 6.0
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a U-handle {width:.1f}x{height:.1f}mm with R{profile_radius:.1f}mm profile',
            'parameters': {
                'width': width,
                'height': height,
                'profile_radius': profile_radius
            },
            'operations': [
                # Profile sketch (circle)
                {
                    'type': 'sketch',
                    'plane': 'YZ',
                    'geometry': 'circle',
                    'params': {'radius': profile_radius, 'center': [0, 0]}
                },
                # Path sketch (U-shape)
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'multi',
                    'items': [
                        # Vertical leg 1
                        {'type': 'line', 'params': {'start': [0, 0], 'end': [0, height]}},
                        # Horizontal top
                        {'type': 'line', 'params': {'start': [0, height], 'end': [width, height]}},
                        # Vertical leg 2
                        {'type': 'line', 'params': {'start': [width, height], 'end': [width, 0]}},
                        # Fillet corners
                        {'type': 'fillet_sketch', 'params': {'radius': 10, 'vertex': [0, height]}},
                        {'type': 'fillet_sketch', 'params': {'radius': 10, 'vertex': [width, height]}}
                    ]
                },
                {
                    'type': 'sweep',
                    'profile_sketch': 1,
                    'path_sketch': 2
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': width + profile_radius * 2,
                'y': height + profile_radius * 2,
                'z': profile_radius * 2
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_propeller_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a simplified propeller using extrude and pattern"""
        hub_radius = random.uniform(10, 20) if difficulty > 1 else 15.0
        blade_length = random.uniform(20, 40) if difficulty > 1 else 25.0
        blade_width = random.uniform(8, 15) if difficulty > 1 else 10.0
        blade_count = random.randint(3, 5) if difficulty > 1 else 3
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a propeller with {blade_count} blades, R{hub_radius:.1f}mm hub',
            'parameters': {
                'hub_radius': hub_radius,
                'blade_length': blade_length,
                'blade_count': blade_count
            },
            'operations': [
                # Hub
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'circle',
                    'params': {'radius': hub_radius, 'center': [0, 0]}
                },
                {
                    'type': 'extrude',
                    'distance': hub_radius
                },
                # Single blade
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'offset': hub_radius / 2,
                    'geometry': 'rectangle',
                    'params': {
                        'width': blade_length,
                        'height': blade_width,
                        'center': [hub_radius + blade_length/2, 0]
                    }
                },
                {
                    'type': 'extrude',
                    'distance': hub_radius * 0.3,
                    'operation': 'join'
                },
                # Pattern blades around hub
                {
                    'type': 'circular_pattern',
                    'count': blade_count,
                    'angle': 360
                },
                # Fillet edges
                {
                    'type': 'fillet',
                    'edges': 'all',
                    'radius': 1.0
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': (hub_radius + blade_length) * 2,
                'y': (hub_radius + blade_length) * 2,
                'z': hub_radius
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_enclosure_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate an enclosure creation task using shell"""
        width = random.uniform(60, 100) if difficulty > 1 else 80.0
        depth = random.uniform(40, 80) if difficulty > 1 else 60.0
        height = random.uniform(20, 40) if difficulty > 1 else 30.0
        wall_thickness = random.uniform(1, 3) if difficulty > 1 else 2.0
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create an enclosure {width:.1f}x{depth:.1f}x{height:.1f}mm with {wall_thickness:.1f}mm walls',
            'parameters': {
                'width': width,
                'depth': depth,
                'height': height,
                'wall_thickness': wall_thickness
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'rectangle',
                    'params': {'width': width, 'height': depth}
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_1',
                    'distance': height
                },
                {
                    'type': 'fillet',
                    'edges': 'all_outer_vertical',
                    'radius': 5.0
                },
                {
                    'type': 'shell',
                    'thickness': wall_thickness
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': width,
                'y': depth,
                'z': height
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_shaft_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a multi-diameter shaft creation task"""
        length = random.uniform(50, 100) if difficulty > 1 else 80.0
        d1 = random.uniform(20, 30) if difficulty > 1 else 25.0
        d2 = random.uniform(10, 18) if difficulty > 1 else 15.0
        d3 = random.uniform(15, 25) if difficulty > 1 else 20.0
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a stepped shaft L{length:.1f}mm with diameters {d1:.1f}/{d2:.1f}/{d3:.1f}mm',
            'parameters': {
                'length': length,
                'd1': d1,
                'd2': d2,
                'd3': d3
            },
            'operations': [
                {
                    'type': 'sketch',
                    'plane': 'XZ',
                    'geometry': 'shaft_profile', # Needs implementation in Fusion script or use composite rectangles
                    'params': {
                        'length': length,
                        'd1': d1,
                        'd2': d2,
                        'd3': d3
                    }
                },
                {
                    'type': 'revolve',
                    'profile': 'sketch_1',
                    'axis': 'X', # Revolve around X axis for shaft
                    'angle': 360
                },
                {
                    'type': 'chamfer',
                    'edges': 'all',
                    'distance': 0.5
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': length,
                'y': max(d1, d2, d3),
                'z': max(d1, d2, d3)
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_ribbed_plate_task(self, task_id: str, difficulty: int) -> Dict:
        """Generate a plate with ribbed reinforcements using linear pattern"""
        length = random.uniform(80, 120) if difficulty > 1 else 100.0
        width = random.uniform(50, 80) if difficulty > 1 else 60.0
        thickness = random.uniform(4, 8) if difficulty > 1 else 5.0
        rib_count = random.randint(3, 6) if difficulty > 1 else 4
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a plate {length:.1f}x{width:.1f}mm with {rib_count} ribs',
            'parameters': {
                'length': length,
                'width': width,
                'thickness': thickness,
                'rib_count': rib_count
            },
            'operations': [
                # Base Plate
                {
                    'type': 'sketch',
                    'plane': 'XY',
                    'geometry': 'rectangle',
                    'params': {'width': length, 'height': width, 'center': [0, 0]}
                },
                {
                    'type': 'extrude',
                    'distance': thickness
                },
                # Rib Profile
                {
                    'type': 'sketch',
                    'plane': 'XZ', # Perpendicular to plate
                    'geometry': 'rectangle',
                    'params': {
                        'width': width, 
                        'height': thickness * 2,
                        'center': [0, thickness] # Sit on top of plate
                    }
                },
                {
                    'type': 'extrude',
                    'profile': 'sketch_2',
                    'distance': thickness # Rib thickness
                },
                # Pattern Ribs
                {
                    'type': 'linear_pattern',
                    'count': rib_count,
                    'distance': length - 20, # Spread across length
                    'direction': 'X'
                }
            ],
            'export_formats': ['stl'],
            'target_dimensions': {
                'x': length,
                'y': width,
                'z': thickness * 2 # Approx height with ribs
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_complex_random_part(self, task_id: str, difficulty: int) -> Dict:
        """Generate a complex random part by chaining operations"""
        # 1. Create Base Shape
        base_type = random.choice(['box', 'cylinder'])
        operations = []
        
        if base_type == 'box':
            width = random.uniform(50, 100)
            depth = random.uniform(50, 100)
            height = random.uniform(20, 50)
            operations.append({
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'rectangle',
                'params': {'width': width, 'height': depth, 'center': [0, 0]}
            })
            operations.append({'type': 'extrude', 'distance': height})
            dims = {'x': width, 'y': depth, 'z': height}
        else:
            radius = random.uniform(25, 50)
            height = random.uniform(30, 80)
            operations.append({
                'type': 'sketch',
                'plane': 'XY',
                'geometry': 'circle',
                'params': {'radius': radius, 'center': [0, 0]}
            })
            operations.append({'type': 'extrude', 'distance': height})
            dims = {'x': radius*2, 'y': radius*2, 'z': height}
            
        # 2. Add Random Features (3-8 features)
        num_features = random.randint(3, 8)
        if difficulty > 1:
            num_features += random.randint(2, 5)
            
        for i in range(num_features):
            feature_type = random.choice(['cut', 'boss', 'hole', 'fillet', 'chamfer'])
            
            if feature_type == 'cut':
                # Random cut on top face
                cut_depth = random.uniform(5, height/2)
                if base_type == 'box':
                    w = random.uniform(10, width/2)
                    h = random.uniform(10, depth/2)
                    operations.append({
                        'type': 'sketch',
                        'plane': 'XY',
                        'offset': height,
                        'geometry': 'rectangle',
                        'params': {'width': w, 'height': h, 'center': [0, 0]}
                    })
                else:
                    r = random.uniform(5, radius/2)
                    operations.append({
                        'type': 'sketch',
                        'plane': 'XY',
                        'offset': height,
                        'geometry': 'circle',
                        'params': {'radius': r, 'center': [0, 0]}
                    })
                operations.append({'type': 'extrude', 'distance': -cut_depth, 'operation': 'cut'})
                
            elif feature_type == 'boss':
                # Random boss (add material)
                boss_height = random.uniform(5, 20)
                if base_type == 'box':
                    w = random.uniform(10, width/3)
                    h = random.uniform(10, depth/3)
                    operations.append({
                        'type': 'sketch',
                        'plane': 'XY',
                        'offset': height,
                        'geometry': 'rectangle',
                        'params': {'width': w, 'height': h, 'center': [random.uniform(-width/4, width/4), random.uniform(-depth/4, depth/4)]}
                    })
                else:
                    r = random.uniform(5, radius/3)
                    operations.append({
                        'type': 'sketch',
                        'plane': 'XY',
                        'offset': height,
                        'geometry': 'circle',
                        'params': {'radius': r, 'center': [random.uniform(-radius/3, radius/3), random.uniform(-radius/3, radius/3)]}
                    })
                operations.append({'type': 'extrude', 'distance': boss_height, 'operation': 'join'})
                dims['z'] += boss_height
                
            elif feature_type == 'hole':
                # Through hole
                hole_r = random.uniform(2, 5)
                operations.append({
                    'type': 'sketch',
                    'plane': 'XY',
                    'offset': height + 10, # Start above
                    'geometry': 'circle',
                    'params': {'radius': hole_r, 'center': [random.uniform(-10, 10), random.uniform(-10, 10)]}
                })
                operations.append({'type': 'extrude', 'distance': -(height + 20), 'operation': 'cut'})
                
            elif feature_type == 'fillet':
                operations.append({'type': 'fillet', 'edges': 'all', 'radius': random.uniform(0.5, 2.0)})
                
            elif feature_type == 'chamfer':
                operations.append({'type': 'chamfer', 'edges': 'all', 'distance': random.uniform(0.5, 1.5)})
        
        return {
            'task_id': task_id,
            'type': 'create_part',
            'description': f'Create a complex random part with {num_features} features',
            'parameters': {'base_type': base_type, 'features': num_features},
            'operations': operations,
            'export_formats': ['stl'],
            'target_dimensions': dims,
            'timestamp': datetime.now().isoformat()
        }

    def submit_task(self, task: Dict):
        print(f"  Description: {task['description']}")
    
    def wait_for_result(self, task_id: str, timeout: int = 300) -> Optional[Dict]:
        """Wait for Fusion 360 to complete the task"""
        result_file = self.results_dir / f"result_{task_id}.json"
        error_file = self.shared_dir / "fusion_error.txt"
        
        print(f"⏳ Waiting for Fusion 360 to complete task...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for successful result
            if result_file.exists():
                with open(result_file, 'r') as f:
                    result = json.load(f)
                
                # Delete result file to mark as processed
                result_file.unlink()
                
                print(f"✓ Task completed in {result['execution_time_seconds']:.1f}s")
                return result
            
            # Check for critical Fusion error
            if error_file.exists():
                with open(error_file, 'r') as f:
                    error_msg = f.read()
                
                # Clean up error file
                error_file.unlink()
                
                print(f"\n🚨 CRITICAL FUSION 360 ERROR 🚨")
                print(f"{'='*40}")
                print(error_msg)
                print(f"{'='*40}\n")
                return None
            
            time.sleep(1)
        
        print(f"✗ Timeout waiting for task completion")
        return None
    
    def analyze_result(self, task: Dict, result: Dict) -> Dict:
        """Analyze the result and generate feedback"""
        if result['status'] != 'success':
            return {
                'feedback': {
                    'overall_score': 0.0,
                    'strengths': [],
                    'issues': result.get('errors', ['Task failed']),
                    'suggestions': ['Review the task requirements and try again']
                }
            }
        
        # Get the exported STL file
        stl_path = Path(result['exports'].get('stl', ''))
        
        if not stl_path.exists():
            return {
                'feedback': {
                    'overall_score': 0.0,
                    'strengths': [],
                    'issues': ['STL file not found'],
                    'suggestions': ['Check Fusion 360 export settings']
                }
            }
        
        # Analyze the model
        target_dims = task.get('target_dimensions')
        analysis_result = analyze_model(stl_path, target_dims)
        
        return analysis_result
    
    def save_session_data(self, task: Dict, result: Dict, analysis: Dict):
        """Save training session data"""
        session_data = {
            'task': task,
            'result': result,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        session_file = self.session_dir / f"{task['task_id']}_session.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def generate_learning_summary(self, task: Dict, analysis: Dict) -> str:
        """Generate learning summary and update memory based on feedback"""
        score = analysis['feedback']['overall_score']
        task_type = task['type']
        task_desc = task.get('description', '')
        issues = analysis['feedback'].get('issues', [])
        suggestions = analysis['feedback'].get('suggestions', [])
        
        # Detect specific patterns and update learning memory
        lesson = None
        
        # Check for chamfer/fillet issues
        if any('sharp corners' in str(s).lower() or 'chamfer' in str(s).lower() or 'fillet' in str(s).lower() for s in suggestions):
            if 'chamfer' not in str(issues).lower():  # Chamfers exist but still getting feedback
                # Chamfers might be too small
                self.learning_memory['parameter_adjustments']['chamfer_scale_factor'] *= 1.1
                lesson = "Chamfers may be too small - increasing size by 10%"
        
        # Check for acute angle issues (chamfers too small or missing)
        if any('acute angle' in str(i).lower() for i in issues):
            self.learning_memory['parameter_adjustments']['chamfer_scale_factor'] *= 1.15
            lesson = "Acute angles detected - increasing chamfer size by 15%"
        
        # Check for repetition (same parameters)
        if 'variety_boost' in self.learning_memory['parameter_adjustments']:
            # Track if we're seeing similar scores repeatedly
            if not hasattr(self, '_recent_scores'):
                self._recent_scores = []
            self._recent_scores.append(score)
            if len(self._recent_scores) > 5:
                self._recent_scores.pop(0)
                # If scores are very similar, increase variety
                if len(set([round(s) for s in self._recent_scores])) <= 2:
                    self.learning_memory['parameter_adjustments']['variety_boost'] += 0.1
                    lesson = "Repetitive results - increasing parameter variety"
        
        # Track common issues
        for issue in issues:
            issue_key = str(issue)[:50]  # Truncate for storage
            if issue_key not in self.learning_memory['common_issues']:
                self.learning_memory['common_issues'][issue_key] = 0
            self.learning_memory['common_issues'][issue_key] += 1
        
        # Add lesson to memory
        if lesson:
            self.learning_memory['lessons_learned'].append({
                'timestamp': datetime.now().isoformat(),
                'lesson': lesson,
                'task_type': task_type,
                'score': score
            })
            # Keep only last 20 lessons
            if len(self.learning_memory['lessons_learned']) > 20:
                self.learning_memory['lessons_learned'] = self.learning_memory['lessons_learned'][-20:]
        
        # Save updated memory
        self.save_learning_memory()
        
        # Generate summary message
        if score >= 90:
            summary = f"Mastered {task_type}! Strategy effective. Ready for higher difficulty."
        elif score >= 70:
            summary = f"Good progress on {task_type}. Minor refinement needed: {suggestions[0] if suggestions else 'Optimize geometry'}."
        else:
            issue = issues[0] if issues else "Unknown error"
            suggestion = suggestions[0] if suggestions else "Review parameters"
            summary = f"Failed {task_type} ({score:.1f}). Issue: {issue}. Action: {suggestion}."
        
        # Append lesson if learned something new
        if lesson:
            summary += f" 📚 Learned: {lesson}"
        
        return summary
            
    def update_progress(self, task: Dict, analysis: Dict):
        """Update overall training progress"""
        score = analysis['feedback']['overall_score']
        
        self.progress['completed_tasks'] += 1
        self.progress['total_score'] += score
        
        task_type = task.get('type', 'unknown')
        if task_type not in self.progress['best_scores']:
            self.progress['best_scores'][task_type] = score
        else:
            self.progress['best_scores'][task_type] = max(
                self.progress['best_scores'][task_type], 
                score
            )
        
        self.progress['session_history'].append({
            'session_id': self.session_id,
            'task_id': task['task_id'],
            'score': score,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_progress()
    
    def print_feedback(self, analysis: Dict):
        """Print feedback in a readable format"""
        feedback = analysis['feedback']
        
        print("\n" + "="*70)
        print("FEEDBACK REPORT")
        print("="*70)
        print(f"\n📊 Overall Score: {feedback.get('overall_score', 0.0):.1f}/100")
        
        if feedback.get('strengths'):
            print("\n✅ STRENGTHS:")
            for strength in feedback['strengths']:
                print(f"   {strength}")
        
        if feedback.get('issues'):
            print("\n⚠️  ISSUES:")
            for issue in feedback['issues']:
                print(f"   {issue}")
        
        if feedback.get('suggestions'):
            print("\n💡 SUGGESTIONS:")
            for suggestion in feedback['suggestions']:
                print(f"   • {suggestion}")
        
        print("\n" + "="*70 + "\n")
    
    def run_training_session(self, task_types: List[str], iterations: int = 5):
        """Run a training session with multiple tasks"""
        print(f"\n🚀 Starting training session: {self.session_id}")
        print(f"   Task types: {', '.join(task_types)}")
        print(f"   Iterations: {iterations}\n")
        
        for i in range(iterations):
            print(f"\n--- Iteration {i+1}/{iterations} ---")
            
            # Select random task type
            task_type = random.choice(task_types)
            
            # Generate task
            task = self.generate_task(task_type, difficulty=self.current_level)
            
            # Submit to Fusion 360
            self.submit_task(task)
            
            # Wait for completion
            result = self.wait_for_result(task['task_id'])
            
            if result is None:
                print("⚠️  Skipping to next task due to timeout")
                continue
            
            # Analyze result
            analysis = self.analyze_result(task, result)
            
            # Print feedback
            self.print_feedback(analysis)
            
            # Generate and print learning summary
            summary = self.generate_learning_summary(task, analysis)
            print(f"\n🧠 LEARNING INSIGHT: {summary}\n")
            
            # Save session data
            self.save_session_data(task, result, analysis)
            
            # Update progress
            self.update_progress(task, analysis)
        
        # Print session summary
        self.print_session_summary()
    
    def print_session_summary(self):
        """Print summary of the training session"""
        avg_score = self.progress['total_score'] / max(1, self.progress['completed_tasks'])
        
        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)
        print(f"Session ID: {self.session_id}")
        print(f"Tasks Completed: {self.progress['completed_tasks']}")
        print(f"Average Score: {avg_score:.1f}/100")
        print(f"Current Level: {self.current_level}")
        print("\nBest Scores by Task Type:")
        for task_type, score in self.progress['best_scores'].items():
            print(f"  {task_type}: {score:.1f}/100")
        print("="*70 + "\n")


class TeeLogger:
    """Writes output to both stdout/stderr and a file"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


if __name__ == '__main__':
    import sys
    
    # Get workspace directory
    workspace = Path(__file__).parent
    
    # Set up logging to file
    log_file = workspace / "orchestrator.log"
    sys.stdout = TeeLogger(log_file)
    # Redirect stderr to the same logger for unified error tracking
    sys.stderr = sys.stdout
    
    print(f"📝 Logging output to: {log_file}")
    
    # Create orchestrator
    orchestrator = TrainingOrchestrator(workspace)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-mode':
            # Test mode - single task
            task_type = sys.argv[2] if len(sys.argv) > 2 else 'simple_cylinder'
            print(f"🧪 Test Mode: Running single {task_type} task\n")
            
            # Generate task
            task = orchestrator.generate_task(task_type, difficulty=1)
            orchestrator.submit_task(task)
            result = orchestrator.wait_for_result(task['task_id'])
            
            if result:
                analysis = orchestrator.analyze_result(task, result)
                orchestrator.print_feedback(analysis)
                
        elif sys.argv[1] == '--run-file':
            # Run specific task file
            task_file = Path(sys.argv[2])
            print(f"🧪 Running task from file: {task_file}\n")
            
            if task_file.exists():
                with open(task_file, 'r') as f:
                    task = json.load(f)
                
                # Start log streamer
                log_file = workspace / "shared" / "fusion_logs.jsonl"
                streamer = LogStreamer(log_file)
                streamer.start()
                
                print(f"{Colors.CYAN}{'─' * 70}{Colors.RESET}")
                print(f"{Colors.BOLD}FUSION 360 EXECUTION LOG{Colors.RESET}")
                print(f"{Colors.CYAN}{'─' * 70}{Colors.RESET}\n")
                
                orchestrator.submit_task(task)
                result = orchestrator.wait_for_result(task['task_id'])
                
                # Stop streamer and print summary
                streamer.stop()
                streamer.print_summary()
                
                if result:
                    analysis = orchestrator.analyze_result(task, result)
                    orchestrator.print_feedback(analysis)
            else:
                print(f"❌ Task file not found: {task_file}")
                
        else:
            # Normal training mode
            orchestrator.run_training_session(iterations=10)
    else:
        # Default to training mode
        orchestrator.run_training_session(iterations=10)
