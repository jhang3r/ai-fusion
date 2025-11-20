"""
Fusion 360 Task Processor Module
Contains all CAD operation logic - can be hot-reloaded without restarting Fusion
"""

import adsk.core
import adsk.fusion
import json
import os
import time
import math
from datetime import datetime

# These will be set by the loader
RESULTS_DIR = None
EXPORTS_DIR = None

# Log file for streaming to orchestrator
LOG_FILE = None


def write_log(level, message, operation=None, context=None, task_id=None):
    """Write a log entry in JSON Lines format for streaming"""
    global LOG_FILE
    
    # Auto-initialize LOG_FILE if not set
    if not LOG_FILE:
        try:
            # Calculate path relative to this file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            shared_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'shared')
            LOG_FILE = os.path.join(shared_dir, 'fusion_logs.jsonl')
        except:
            return  # Can't determine path, give up
    
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'operation': operation,
            'context': context or {},
            'task_id': task_id
        }
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
            f.flush()  # Force write to disk
    except Exception as e:
        # Write error to a fallback location for debugging
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            error_log = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'shared', 'fusion_error_log.txt')
            with open(error_log, 'a') as f:
                f.write(f"write_log failed: {str(e)}, LOG_FILE={LOG_FILE}\n")
        except:
            pass


class TaskProcessor:
    """Processes design tasks from JSON files"""
    
    def __init__(self, app, ui):
        self.app = app
        self.ui = ui
        self.design = None
        self.root_comp = None
        self.current_task_id = None
        self.current_operation = None
        
    def log(self, message, level='INFO', context=None):
        """Log message to Text Commands palette and JSON log file"""
        # Write to palette
        try:
            palette = self.ui.palettes.itemById('TextCommands')
            if palette:
                if not palette.isVisible:
                    palette.isVisible = True
                palette.writeText(message)
        except:
            pass
        
        # Write to JSON log file
        write_log(level, message, self.current_operation, context, self.current_task_id)
        
    def process_task_file(self, task_file):
        """Process a single task file"""
        try:
            # Read task
            with open(task_file, 'r') as f:
                task = json.load(f)
            
            task_id = task['task_id']
            description = task.get('description', 'No description')
            task_type = task.get('type', 'unknown')
            
            # Set task ID for logging
            self.current_task_id = task_id
            
            # Test log write
            write_log('INFO', f'LOG FILE TEST: {LOG_FILE}', None, None, task_id)
            
            self.log(f"🚀 v1.1 ASSEMBLY SUPPORT - Processing: {task_type}")
            self.log(f"Goal: {description}")
            
            # Create new document
            doc = self.app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            self.design = adsk.fusion.Design.cast(self.app.activeProduct)
            self.root_comp = self.design.rootComponent
            
            # Name the component for visibility
            try:
                self.root_comp.name = f"{task_type}_{task_id[-4:]}"
            except:
                pass
            
            # Execute operations
            start_time = time.time()
            errors = []
            
            for operation in task.get('operations', []):
                try:
                    self.execute_operation(operation)
                except Exception as e:
                    errors.append(f"Operation {operation['type']}: {str(e)}")
            
            execution_time = time.time() - start_time
            
            # Export models
            exports = {}
            for export_format in task.get('export_formats', ['stl']):
                try:
                    export_path = self.export_model(task_id, export_format)
                    exports[export_format] = export_path
                except Exception as e:
                    errors.append(f"Export {export_format}: {str(e)}")
            
            # Gather metadata
            metadata = self.gather_metadata()
            
            # Write result
            result = {
                'task_id': task_id,
                'status': 'success' if not errors else 'partial_success',
                'exports': exports,
                'metadata': metadata,
                'execution_time_seconds': execution_time,
                'errors': errors,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
            }
            
            result_file = os.path.join(RESULTS_DIR, f"result_{task_id}.json")
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Delete task file to mark as processed
            try:
                os.remove(task_file)
            except:
                pass # Might have been deleted already
            
            # Check for interferences in assemblies
            if task.get('type') == 'create_assembly':
                interference_count = self.check_interferences()
                if interference_count > 0:
                    errors.append(f"Found {interference_count} interference(s) between components")
            
            self.log(f"Task {task_id} completed!")
            
        except Exception as e:
            self.log(f"Error processing task: {str(e)}")
        
        finally:
            # PAUSE so user can see the model before closing
            # Use doEvents() instead of time.sleep() to keep UI responsive
            self.log("Pausing for viewing...")
            start_pause = time.time()
            while time.time() - start_pause < 4:
                adsk.doEvents()
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
            
            # Close document without saving to prevent clutter
            if 'doc' in locals() and doc:
                doc.close(False)
    
    def execute_operation(self, operation):
        """Execute a single CAD operation"""
        op_type = operation['type']
        self.current_operation = op_type
        self.log(f"Executing operation: {op_type}")
        
        if op_type == 'sketch':
            self.create_sketch(operation)
        elif op_type == 'extrude':
            self.create_extrude(operation)
        elif op_type == 'revolve':
            self.create_revolve(operation)
        elif op_type == 'loft':
            self.create_loft(operation)
        elif op_type == 'sweep':
            self.create_sweep(operation)
        elif op_type == 'circular_pattern':
            self.create_circular_pattern(operation)
        elif op_type == 'linear_pattern':
            self.create_linear_pattern(operation)
        elif op_type == 'shell':
            self.create_shell(operation)
        elif op_type == 'hole':
            self.create_hole(operation)
        elif op_type == 'fillet':
            self.create_fillet(operation)
        elif op_type == 'chamfer':
            self.create_chamfer(operation)
        elif op_type == 'combine':
            self.create_combine(operation)
        elif op_type == 'create_component':
            self.create_component(operation)
        elif op_type == 'activate_component':
            self.activate_component(operation)
        elif op_type == 'create_joint':
            self.create_joint(operation)
        elif op_type == 'transform_component':
            self.transform_component(operation)
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
    
    def create_sketch(self, operation):
        """Create a sketch with geometry"""
        plane_name = operation.get('plane', 'XY')
        
        if plane_name == 'XY':
            plane = self.root_comp.xYConstructionPlane
        elif plane_name == 'XZ':
            plane = self.root_comp.xZConstructionPlane
        elif plane_name == 'YZ':
            plane = self.root_comp.yZConstructionPlane
        else:
            raise ValueError(f"Unknown plane: {plane_name}")
        
        # Handle offset if specified
        offset = float(operation.get('offset', 0.0)) / 10.0  # Convert mm to cm
        if abs(offset) > 0.001:
            planes = self.root_comp.constructionPlanes
            plane_input = planes.createInput()
            offset_value = adsk.core.ValueInput.createByReal(offset)
            plane_input.setByOffset(plane, offset_value)
            plane = planes.add(plane_input)
            self.log(f"Created offset plane from {plane_name} at {offset*10}mm")
        
        sketch = self.root_comp.sketches.add(plane)
        
        # Handle construction geometry
        construction_ops = operation.get('construction_geometry', [])
        for const_op in construction_ops:
            self.create_construction_geometry(sketch, const_op)

        geometry_type = operation.get('geometry', 'rectangle')
        params = operation.get('params', {})
        
        # Handle multi-geometry (multiple items in one sketch)
        if geometry_type == 'multi':
            items = operation.get('items', [])
            self.log(f"Multi-geometry sketch with {len(items)} items")
            for item in items:
                item_type = item.get('type', 'circle')
                item_params = item.get('params', {})
                self._create_geometry(sketch, item_type, item_params)
        else:
            # Single geometry item
            self._create_geometry(sketch, geometry_type, params)
            
        # Apply constraints if specified
        constraints = operation.get('constraints', [])
        if constraints:
            self.apply_constraints(sketch, constraints)
            
        return sketch
    
    def _create_geometry(self, sketch, geometry_type, params):
        """Helper to create a single geometry item in a sketch"""
        if geometry_type == 'rectangle':
            self.sketch_rectangle(sketch, params)
        elif geometry_type == 'circle':
            self.sketch_circle(sketch, params)
        elif geometry_type == 'line':
            self.sketch_line(sketch, params)
        elif geometry_type == 'arc':
            self.sketch_arc(sketch, params)
        elif geometry_type == 'polygon':
            self.sketch_polygon(sketch, params)
        elif geometry_type == 'slot':
            self.sketch_slot(sketch, params)
        elif geometry_type == 'spline':
            self.sketch_spline(sketch, params)
        elif geometry_type == 'gear_profile':
            self.sketch_gear(sketch, params)
        elif geometry_type == 'l_shape':
            self.sketch_l_shape(sketch, params)
        elif geometry_type == 'bottle_profile':
            self.sketch_bottle_profile(sketch, params)
        elif geometry_type == 'shaft_profile':
            self.sketch_shaft_profile(sketch, params)
        elif geometry_type == 'circular_pattern':
            self.sketch_circular_pattern(sketch, params)
        elif geometry_type == 'linear_pattern':
            self.sketch_linear_pattern(sketch, params)
        else:
            self.log(f"Unknown geometry type: {geometry_type}", level='WARNING')
    
    def sketch_circular_pattern(self, sketch, params):
        """Create a circular pattern of geometry (circles/points)"""
        # Pattern parameters
        count = int(params.get('count', 4))
        center = params.get('center', [0, 0]) # Center of pattern
        center_x = float(center[0]) / 10.0
        center_y = float(center[1]) / 10.0
        angle_total = math.radians(float(params.get('angle', 360.0)))
        
        # Base geometry parameters
        base_type = params.get('base_type', 'circle')
        base_params = params.get('base_params', {})
        
        # Calculate angle step
        if abs(angle_total - 2*math.pi) < 0.001:
            step = angle_total / count
        else:
            step = angle_total / (count - 1) if count > 1 else 0
            
        # Create instances
        for i in range(count):
            angle = i * step
            
            # Calculate position for this instance
            # We assume base_params has a position relative to pattern center?
            # Or base_params defines the FIRST instance position?
            # Let's assume base_params defines the first instance in GLOBAL coords.
            # Then we rotate it around pattern center.
            
            # Get first instance position
            if 'center' in base_params:
                p_x = float(base_params['center'][0]) / 10.0
                p_y = float(base_params['center'][1]) / 10.0
            else:
                p_x, p_y = 0, 0
                
            # Relative to pattern center
            rel_x = p_x - center_x
            rel_y = p_y - center_y
            
            # Rotate
            rot_x = rel_x * math.cos(angle) - rel_y * math.sin(angle)
            rot_y = rel_x * math.sin(angle) + rel_y * math.cos(angle)
            
            # New absolute position
            new_x = center_x + rot_x
            new_y = center_y + rot_y
            
            # Create geometry at new position
            if base_type == 'circle':
                radius = float(base_params.get('radius', 5.0)) / 10.0
                sketch.sketchCurves.sketchCircles.addByCenterRadius(
                    adsk.core.Point3D.create(new_x, new_y, 0), radius)
            elif base_type == 'point':
                sketch.sketchPoints.add(adsk.core.Point3D.create(new_x, new_y, 0))

    def sketch_linear_pattern(self, sketch, params):
        """Create a linear pattern of geometry"""
        count = int(params.get('count', 3))
        dx = float(params.get('dx', 10.0)) / 10.0
        dy = float(params.get('dy', 0.0)) / 10.0
        
        base_type = params.get('base_type', 'circle')
        base_params = params.get('base_params', {})
        
        # Get start position
        if 'center' in base_params:
            start_x = float(base_params['center'][0]) / 10.0
            start_y = float(base_params['center'][1]) / 10.0
        else:
            start_x, start_y = 0, 0
            
        for i in range(count):
            new_x = start_x + (i * dx)
            new_y = start_y + (i * dy)
            
            if base_type == 'circle':
                radius = float(base_params.get('radius', 5.0)) / 10.0
                sketch.sketchCurves.sketchCircles.addByCenterRadius(
                    adsk.core.Point3D.create(new_x, new_y, 0), radius)
            elif base_type == 'point':
                sketch.sketchPoints.add(adsk.core.Point3D.create(new_x, new_y, 0))

    
    def sketch_line(self, sketch, params):
        """Draw a single line or series of lines"""
        points = params.get('points', [])
        if len(points) < 2:
            return
            
        lines = sketch.sketchCurves.sketchLines
        
        # Convert all points to cm
        pts_cm = []
        for p in points:
            pts_cm.append(adsk.core.Point3D.create(float(p[0])/10.0, float(p[1])/10.0, 0))
            
        # Draw lines connecting points
        for i in range(len(pts_cm) - 1):
            lines.addByTwoPoints(pts_cm[i], pts_cm[i+1])
            
        # Close loop if requested
        if params.get('close', False):
            lines.addByTwoPoints(pts_cm[-1], pts_cm[0])

    def sketch_arc(self, sketch, params):
        """Draw an arc"""
        arc_type = params.get('type', 'center_radius')
        arcs = sketch.sketchCurves.sketchArcs
        
        if arc_type == 'center_radius':
            center = params.get('center', [0, 0])
            radius = float(params.get('radius', 10.0)) / 10.0
            start_angle = math.radians(float(params.get('start_angle', 0.0)))
            end_angle = math.radians(float(params.get('end_angle', 90.0)))
            
            center_pt = adsk.core.Point3D.create(float(center[0])/10.0, float(center[1])/10.0, 0)
            arcs.addByCenterStartSweep(center_pt, 
                adsk.core.Point3D.create(center_pt.x + radius * math.cos(start_angle), center_pt.y + radius * math.sin(start_angle), 0), 
                end_angle - start_angle)
                
        elif arc_type == '3_point':
            p1 = params.get('start', [0, 0])
            p2 = params.get('end', [10, 0])
            p3 = params.get('point_on_arc', [5, 5])
            
            pt1 = adsk.core.Point3D.create(float(p1[0])/10.0, float(p1[1])/10.0, 0)
            pt2 = adsk.core.Point3D.create(float(p2[0])/10.0, float(p2[1])/10.0, 0)
            pt3 = adsk.core.Point3D.create(float(p3[0])/10.0, float(p3[1])/10.0, 0)
            
            arcs.addByThreePoints(pt1, pt3, pt2)

    def sketch_polygon(self, sketch, params):
        """Draw a regular polygon"""
        sides = int(params.get('sides', 6))
        radius = float(params.get('radius', 10.0)) / 10.0
        center = params.get('center', [0, 0])
        
        center_pt = adsk.core.Point3D.create(float(center[0])/10.0, float(center[1])/10.0, 0)
        
        points = []
        for i in range(sides):
            angle = (2 * math.pi * i) / sides
            x = center_pt.x + radius * math.cos(angle)
            y = center_pt.y + radius * math.sin(angle)
            points.append(adsk.core.Point3D.create(x, y, 0))
            
        lines = sketch.sketchCurves.sketchLines
        for i in range(sides):
            lines.addByTwoPoints(points[i], points[(i+1)%sides])

    def sketch_slot(self, sketch, params):
        """Draw a slot"""
        p1 = params.get('start', [-10, 0])
        p2 = params.get('end', [10, 0])
        diameter = float(params.get('diameter', 5.0)) / 10.0
        radius = diameter / 2.0
        
        pt1 = adsk.core.Point3D.create(float(p1[0])/10.0, float(p1[1])/10.0, 0)
        pt2 = adsk.core.Point3D.create(float(p2[0])/10.0, float(p2[1])/10.0, 0)
        
        # Calculate vector for perpendicular offset
        dx = pt2.x - pt1.x
        dy = pt2.y - pt1.y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 0.001: return
        
        ux = -dy / length * radius
        uy = dx / length * radius
        
        # 4 points of the rectangle part
        r1 = adsk.core.Point3D.create(pt1.x + ux, pt1.y + uy, 0)
        r2 = adsk.core.Point3D.create(pt2.x + ux, pt2.y + uy, 0)
        r3 = adsk.core.Point3D.create(pt2.x - ux, pt2.y - uy, 0)
        r4 = adsk.core.Point3D.create(pt1.x - ux, pt1.y - uy, 0)
        
        lines = sketch.sketchCurves.sketchLines
        arcs = sketch.sketchCurves.sketchArcs
        
        lines.addByTwoPoints(r1, r2)
        lines.addByTwoPoints(r3, r4)
        arcs.addByCenterStartEnd(pt2, r2, r3)
        arcs.addByCenterStartEnd(pt1, r4, r1)

    def sketch_spline(self, sketch, params):
        """Draw a spline through points"""
        points = params.get('points', [])
        if len(points) < 2: return
        
        fit_points = adsk.core.ObjectCollection.create()
        for p in points:
            fit_points.add(adsk.core.Point3D.create(float(p[0])/10.0, float(p[1])/10.0, 0))
            
        sketch.sketchCurves.sketchFittedSplines.add(fit_points)

    def create_construction_geometry(self, sketch, params):
        """Create construction geometry (lines, points)"""
        geom_type = params.get('type', 'line')
        
        if geom_type == 'line':
            p1 = params.get('start', [0, 0])
            p2 = params.get('end', [10, 0])
            
            pt1 = adsk.core.Point3D.create(float(p1[0])/10.0, float(p1[1])/10.0, 0)
            pt2 = adsk.core.Point3D.create(float(p2[0])/10.0, float(p2[1])/10.0, 0)
            
            line = sketch.sketchCurves.sketchLines.addByTwoPoints(pt1, pt2)
            line.isConstruction = True
            
        elif geom_type == 'point':
            p = params.get('point', [0, 0])
            pt = adsk.core.Point3D.create(float(p[0])/10.0, float(p[1])/10.0, 0)
            point = sketch.sketchPoints.add(pt)
            # Points are construction by default in some contexts, but we can't explicitly set isConstruction on SketchPoint

    def apply_constraints(self, sketch, constraints):
        """Apply geometric and dimensional constraints to sketch entities"""
        geom_constraints = sketch.geometricConstraints
        dim_constraints = sketch.sketchDimensions
        
        # Get count of curves BEFORE main geometry to offset indices
        # This is a simplified approach - ideally we'd track entity IDs
        # For now, we'll just try-catch everything to prevent crashes
        
        for constraint in constraints:
            c_type = constraint.get('type')
            
            try:
                if c_type == 'horizontal_vertical':
                    entity_idx = constraint.get('entity_index', -1)
                    # Adjust index for construction lines if needed, or user must supply correct index
                    if entity_idx >= 0 and entity_idx < sketch.sketchCurves.count:
                        entity = sketch.sketchCurves.item(entity_idx)
                        geom_constraints.addHorizontalOrVertical(entity)
                        
                elif c_type == 'dimension_diameter':
                    # Apply to circle/arc
                    idx = constraint.get('entity_index')
                    val = float(constraint.get('value', 10.0)) / 10.0
                    pos = constraint.get('position', [0, 0])
                    text_pt = adsk.core.Point3D.create(float(pos[0])/10.0, float(pos[1])/10.0, 0)
                    
                    if idx is not None:
                        # Safety check: ensure index is valid
                        if idx < 0 or idx >= sketch.sketchCurves.count:
                            self.log(f"Warning: Invalid entity index {idx} for diameter constraint")
                            continue
                            
                        entity = sketch.sketchCurves.item(idx)
                        
                        # Verify entity type (must be circle or arc)
                        if entity.objectType not in [adsk.fusion.SketchCircle.classType(), adsk.fusion.SketchArc.classType()]:
                            self.log(f"Warning: Entity at index {idx} is not a circle/arc (Type: {entity.objectType})")
                            continue
                            
                        dim = dim_constraints.addDiameterDimension(entity, text_pt)
                        dim.parameter.value = val
                        
            except Exception as e:
                self.log(f"Failed to apply constraint {c_type}: {str(e)}")
                # Don't raise - allow other constraints to proceed

    def sketch_rectangle(self, sketch, params):
        """Draw a rectangle centered at origin"""
        # Convert mm to cm
        width = float(params.get('width', 10.0)) / 10.0
        height = float(params.get('height', 10.0)) / 10.0
        
        lines = sketch.sketchCurves.sketchLines
        
        # Calculate corner points (centered)
        p1 = adsk.core.Point3D.create(-width/2, -height/2, 0)
        p2 = adsk.core.Point3D.create(width/2, -height/2, 0)
        p3 = adsk.core.Point3D.create(width/2, height/2, 0)
        p4 = adsk.core.Point3D.create(-width/2, height/2, 0)
        
        lines.addByTwoPoints(p1, p2)
        lines.addByTwoPoints(p2, p3)
        lines.addByTwoPoints(p3, p4)
        lines.addByTwoPoints(p4, p1)


    def sketch_circle(self, sketch, params):
        """Draw a circle"""
        # Convert mm to cm (Fusion internal units)
        radius = float(params.get('radius', 5.0)) / 10.0
        center = params.get('center', [0, 0])
        center_x = float(center[0]) / 10.0
        center_y = float(center[1]) / 10.0
        
        circles = sketch.sketchCurves.sketchCircles
        center_point = adsk.core.Point3D.create(center_x, center_y, 0)
        circles.addByCenterRadius(center_point, radius)

    def sketch_gear(self, sketch, params):
        """Draw a parametric gear profile"""
        # Convert mm to cm
        module = float(params.get('module', 2.0)) / 10.0
        teeth = int(params.get('teeth', 20))
        pressure_angle = math.radians(20)
        
        # Gear calculations
        pitch_diam = module * teeth
        addendum = module
        dedendum = 1.25 * module
        
        root_radius = (pitch_diam / 2.0) - dedendum
        outer_radius = (pitch_diam / 2.0) + addendum
        
        # Points for one tooth
        points = adsk.core.ObjectCollection.create()
        
        for i in range(teeth):
            angle_step = (2 * math.pi) / teeth
            base_angle = i * angle_step
            
            # Simplified trapezoidal tooth profile
            # 4 points per tooth: root start, tip start, tip end, root end
            
            # Angle offsets (approximate for visual correctness)
            a1 = base_angle - (angle_step * 0.25) # Root start
            a2 = base_angle - (angle_step * 0.15) # Tip start
            a3 = base_angle + (angle_step * 0.15) # Tip end
            a4 = base_angle + (angle_step * 0.25) # Root end
            
            # Create points
            p1 = adsk.core.Point3D.create(root_radius * math.cos(a1), root_radius * math.sin(a1), 0)
            p2 = adsk.core.Point3D.create(outer_radius * math.cos(a2), outer_radius * math.sin(a2), 0)
            p3 = adsk.core.Point3D.create(outer_radius * math.cos(a3), outer_radius * math.sin(a3), 0)
            p4 = adsk.core.Point3D.create(root_radius * math.cos(a4), root_radius * math.sin(a4), 0)
            
            points.add(p1)
            points.add(p2)
            points.add(p3)
            points.add(p4)
        
        # Connect points with lines
        lines = sketch.sketchCurves.sketchLines
        for i in range(points.count):
            p_start = points.item(i)
            p_end = points.item((i + 1) % points.count)
            lines.addByTwoPoints(p_start, p_end)
            
        # Add bore hole if specified
        bore = float(params.get('bore', 0.0)) / 10.0
        if bore > 0:
            circles = sketch.sketchCurves.sketchCircles
            center_point = adsk.core.Point3D.create(0, 0, 0)
            circles.addByCenterRadius(center_point, bore / 2.0)
    
    def sketch_l_shape(self, sketch, params):
        """Draw an L-shape profile"""
        # Convert mm to cm
        length = float(params.get('length', 50.0)) / 10.0
        height = float(params.get('height', 40.0)) / 10.0
        thickness = float(params.get('thickness', 10.0)) / 10.0
        width = float(params.get('width', 40.0)) / 10.0 # Not used in sketch but passed for context
        
        lines = sketch.sketchCurves.sketchLines
        
        # L-shape points (starting at origin, going counter-clockwise)
        p1 = adsk.core.Point3D.create(0, 0, 0)
        p2 = adsk.core.Point3D.create(length, 0, 0)
        p3 = adsk.core.Point3D.create(length, thickness, 0)
        p4 = adsk.core.Point3D.create(thickness, thickness, 0)
        p5 = adsk.core.Point3D.create(thickness, height, 0)
        p6 = adsk.core.Point3D.create(0, height, 0)
        
        lines.addByTwoPoints(p1, p2)
        lines.addByTwoPoints(p2, p3)
        lines.addByTwoPoints(p3, p4)
        lines.addByTwoPoints(p4, p5)
        lines.addByTwoPoints(p5, p6)
        lines.addByTwoPoints(p6, p1)

    def sketch_bottle_profile(self, sketch, params):
        """Draw a bottle profile for revolve (half-profile on one side of axis)"""
        # Convert mm to cm
        height = float(params.get('height', 100.0)) / 10.0
        base_radius = float(params.get('base_radius', 25.0)) / 10.0
        neck_radius = float(params.get('neck_radius', 10.0)) / 10.0
        
        lines = sketch.sketchCurves.sketchLines
        
        # Create profile points (starting from bottom on axis, going up and out)
        # Bottom center
        p1 = adsk.core.Point3D.create(0, 0, 0)
        # Bottom edge
        p2 = adsk.core.Point3D.create(base_radius, 0, 0)
        # Mid body
        p3 = adsk.core.Point3D.create(base_radius, height * 0.6, 0)
        # Shoulder
        p4 = adsk.core.Point3D.create(neck_radius, height * 0.8, 0)
        # Neck
        p5 = adsk.core.Point3D.create(neck_radius, height, 0)
        # Top center
        p6 = adsk.core.Point3D.create(0, height, 0)
        
        # Draw profile
        lines.addByTwoPoints(p1, p2)
        lines.addByTwoPoints(p2, p3)
        lines.addByTwoPoints(p3, p4)
        lines.addByTwoPoints(p4, p5)
        lines.addByTwoPoints(p5, p6)
        lines.addByTwoPoints(p6, p1)  # Close profile

    def sketch_shaft_profile(self, sketch, params):
        """Draw a stepped shaft profile for revolve"""
        # Convert mm to cm
        length = float(params.get('length', 80.0)) / 10.0
        d1 = float(params.get('d1', 25.0)) / 10.0
        d2 = float(params.get('d2', 15.0)) / 10.0
        d3 = float(params.get('d3', 20.0)) / 10.0
        
        r1 = d1 / 2.0
        r2 = d2 / 2.0
        r3 = d3 / 2.0
        
        # Segment lengths (approximate 1/3 each)
        l_seg = length / 3.0
        
        lines = sketch.sketchCurves.sketchLines
        
        # Profile points (along X axis)
        p1 = adsk.core.Point3D.create(0, 0, 0)
        p2 = adsk.core.Point3D.create(l_seg, 0, 0)
        p3 = adsk.core.Point3D.create(l_seg * 2, 0, 0)
        p4 = adsk.core.Point3D.create(length, 0, 0)
        
        p5 = adsk.core.Point3D.create(length, r3, 0)
        p6 = adsk.core.Point3D.create(l_seg * 2, r3, 0)
        p7 = adsk.core.Point3D.create(l_seg * 2, r2, 0)
        p8 = adsk.core.Point3D.create(l_seg, r2, 0)
        p9 = adsk.core.Point3D.create(l_seg, r1, 0)
        p10 = adsk.core.Point3D.create(0, r1, 0)
        
        # Draw profile
        lines.addByTwoPoints(p1, p4) # Axis line
        lines.addByTwoPoints(p4, p5)
        lines.addByTwoPoints(p5, p6)
        lines.addByTwoPoints(p6, p7)
        lines.addByTwoPoints(p7, p8)
        lines.addByTwoPoints(p8, p9)
        lines.addByTwoPoints(p9, p10)
        lines.addByTwoPoints(p10, p1) # Close profile
    
    def create_extrude(self, operation):
        """Create an extrusion"""
        sketch = self.root_comp.sketches[-1]
        
        # Convert mm to cm
        distance = float(operation.get('distance', 10.0)) / 10.0
        
        # Determine operation type
        op_type_str = operation.get('operation', 'new').lower()
        if op_type_str == 'cut':
            op_type = adsk.fusion.FeatureOperations.CutFeatureOperation
        elif op_type_str == 'join':
            op_type = adsk.fusion.FeatureOperations.JoinFeatureOperation
        elif op_type_str == 'intersect':
            op_type = adsk.fusion.FeatureOperations.IntersectFeatureOperation
        else:
            op_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        
        extrudes = self.root_comp.features.extrudeFeatures
        
        # Check if we have multiple profiles (e.g., from a circular pattern of circles)
        profile_count = sketch.profiles.count
        
        if profile_count > 1:
            # Multiple profiles - collect all of them
            profiles = adsk.core.ObjectCollection.create()
            for i in range(profile_count):
                profiles.add(sketch.profiles.item(i))
            ext_input = extrudes.createInput(profiles, op_type)
            self.log(f"Extrude: Using {profile_count} profiles")
        else:
            # Single profile
            profile = sketch.profiles[0]
            ext_input = extrudes.createInput(profile, op_type)
            self.log(f"Extrude: Using 1 profile")
        
        distance_value = adsk.core.ValueInput.createByReal(distance)
        ext_input.setDistanceExtent(False, distance_value)
        
        extrudes.add(ext_input)
    
    def create_revolve(self, operation):
        """Create a revolve feature"""
        try:
            self.log("Revolve: Getting profile from last sketch...")
            profile = self.root_comp.sketches[-1].profiles[0]
            self.log(f"Revolve: Profile has {self.root_comp.sketches[-1].profiles.count} profiles")
            
            # Get axis
            axis_name = operation.get('axis', 'Z')
            if axis_name == 'X':
                axis = self.root_comp.xConstructionAxis
            elif axis_name == 'Y':
                axis = self.root_comp.yConstructionAxis
            else:
                axis = self.root_comp.zConstructionAxis
            self.log(f"Revolve: Using {axis_name} axis")
            
            revolves = self.root_comp.features.revolveFeatures
            self.log("Revolve: Creating revolve input...")
            rev_input = revolves.createInput(profile, axis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            
            angle = operation.get('angle', 360.0)
            angle_value = adsk.core.ValueInput.createByReal(math.radians(angle))
            rev_input.setAngleExtent(False, angle_value)
            self.log(f"Revolve: Angle set to {angle}°")
            
            self.log(f"Revolve: Input valid: {rev_input.isValid}")
            if not rev_input.isValid:
                self.log("Revolve: Input is INVALID - checking error message...", level='ERROR')
                # Try to get error message
                try:
                    error_msg = rev_input.errorOrWarningMessage
                    self.log(f"Revolve: Error message: {error_msg}", level='ERROR')
                except:
                    pass
            
            self.log("Revolve: Executing revolves.add()...")
            revolve_feature = revolves.add(rev_input)
            self.log("Revolve: revolves.add() completed")
            
            if revolve_feature and revolve_feature.bodies.count > 0:
                body = revolve_feature.bodies.item(0)
                bbox = body.boundingBox
                x = (bbox.maxPoint.x - bbox.minPoint.x) * 10
                y = (bbox.maxPoint.y - bbox.minPoint.y) * 10
                z = (bbox.maxPoint.z - bbox.minPoint.z) * 10
                self.log(f"Revolve: Created body - size: {x:.1f}mm x {y:.1f}mm x {z:.1f}mm")
            else:
                self.log("Revolve: No bodies created", level='WARNING')
        except Exception as e:
            self.log(f"Revolve operation failed: {str(e)}", level='ERROR')
            import traceback
            self.log(traceback.format_exc())
    def create_loft(self, operation):
        """Create loft between multiple profiles"""
        try:
            # Get profile indices (sketches to loft between)
            profile_indices = operation.get('profiles', [1, 2])
            
            self.log(f"Loft: Attempting to loft between sketch indices: {profile_indices}")
            self.log(f"Loft: Total sketches available: {self.root_comp.sketches.count}")
            
            # Collect profiles
            profiles = []
            for item in profile_indices:
                # Handle both int (legacy) and dict (new) formats
                if isinstance(item, dict):
                    idx = item.get('sketch_index', 0)
                    prof_idx = item.get('profile_index', 0)
                else:
                    idx = int(item)
                    prof_idx = 0
                
                # Use 0-based indexing for safety, assuming input is aligned
                sketch_idx = idx
                
                if sketch_idx < self.root_comp.sketches.count:
                    sketch = self.root_comp.sketches.item(sketch_idx)
                    self.log(f"Loft: Sketch {idx} has {sketch.profiles.count} profiles")
                    
                    if sketch.profiles.count > prof_idx:
                        profile = sketch.profiles.item(prof_idx)
                        if profile and profile.isValid:
                            profiles.append(profile)
                            self.log(f"Loft: Added valid profile from sketch {idx}")
                        else:
                            self.log(f"Loft: Profile from sketch {idx} is invalid", level='ERROR')
            
            self.log(f"Loft: Collected {len(profiles)} profiles")
            
            if len(profiles) >= 2:
                self.log("Loft: Getting loftFeatures...")
                lofts = self.root_comp.features.loftFeatures
                self.log("Loft: Creating loft input...")
                loft_input = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                
                # Add profiles to loft sections using the proper API
                self.log("Loft: Adding profiles to loftSections...")
                loft_sections = loft_input.loftSections
                for i, profile in enumerate(profiles):
                    self.log(f"Loft: Adding profile {i}...")
                    loft_sections.add(profile)
                
                self.log("Loft: Setting isSolid...")
                loft_input.isSolid = True
                
                self.log(f"Loft: Input valid: {loft_input.isValid}")
                
                if loft_input.isValid:
                    self.log("Loft: executing lofts.add()...")
                    loft_feature = lofts.add(loft_input)
                    self.log("Loft: lofts.add() completed")
                    
                    # Log success
                    if loft_feature and loft_feature.bodies.count > 0:
                        body = loft_feature.bodies.item(0)
                        bbox = body.boundingBox
                        x = (bbox.maxPoint.x - bbox.minPoint.x) * 10
                        y = (bbox.maxPoint.y - bbox.minPoint.y) * 10
                        z = (bbox.maxPoint.z - bbox.minPoint.z) * 10
                        self.log(f"Loft: Created body - size: {x:.1f}mm x {y:.1f}mm x {z:.1f}mm")
                    else:
                        self.log(f"Loft: Created but no bodies generated")
                else:
                    self.log("Loft: Input is INVALID", level='ERROR')
            else:
                self.log(f"Loft: FAILED - Need at least 2 profiles, got {len(profiles)}")
        except Exception as e:
            self.log(f"Loft operation failed: {str(e)}", level='ERROR')
            import traceback
            self.log(traceback.format_exc())
    
    def create_sweep(self, operation):
        """Create a sweep feature"""
        try:
            profile_sketch_idx = operation.get('profile_sketch', 1) - 1
            path_sketch_idx = operation.get('path_sketch', 2) - 1
            
            self.log(f"Sweep: Profile sketch index: {profile_sketch_idx}, Path sketch index: {path_sketch_idx}")
            
            if profile_sketch_idx < self.root_comp.sketches.count and path_sketch_idx < self.root_comp.sketches.count:
                profile_sketch = self.root_comp.sketches.item(profile_sketch_idx)
                path_sketch = self.root_comp.sketches.item(path_sketch_idx)
                
                self.log(f"Sweep: Profile sketch has {profile_sketch.profiles.count} profiles")
                self.log(f"Sweep: Path sketch has {path_sketch.sketchCurves.count} curves")
                
                # Get first profile
                profile = profile_sketch.profiles.item(0)
                
                # Create Path from sketch curves
                path_curves = adsk.core.ObjectCollection.create()
                for curve in path_sketch.sketchCurves:
                    path_curves.add(curve)
                
                self.log(f"Sweep: Creating path from {path_curves.count} curves")
                path = self.root_comp.features.createPath(path_curves)
                
                sweeps = self.root_comp.features.sweepFeatures
                sweep_input = sweeps.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                sweep_feature = sweeps.add(sweep_input)
                
                # Log result
                if sweep_feature and sweep_feature.bodies.count > 0:
                    body = sweep_feature.bodies.item(0)
                    bbox = body.boundingBox
                    x = (bbox.maxPoint.x - bbox.minPoint.x) * 10
                    y = (bbox.maxPoint.y - bbox.minPoint.y) * 10
                    z = (bbox.maxPoint.z - bbox.minPoint.z) * 10
                    self.log(f"Sweep: Created body - size: {x:.1f}mm x {y:.1f}mm x {z:.1f}mm")
                else:
                    self.log("Sweep: Created but no bodies generated", level='WARNING')
        except Exception as e:
            self.log(f"Sweep operation failed: {str(e)}", level='ERROR')
    
    def create_circular_pattern(self, operation):
        """Create circular pattern of features"""
        try:
            count = int(operation.get('count', 4))
            angle = float(operation.get('angle', 360.0))
            
            # Get the last feature to pattern
            if self.root_comp.features.count > 0:
                features = adsk.core.ObjectCollection.create()
                features.add(self.root_comp.features.item(self.root_comp.features.count - 1))
                
                # Use Z-axis as default
                axis = self.root_comp.zConstructionAxis
                
                patterns = self.root_comp.features.circularPatternFeatures
                pattern_input = patterns.createInput(features, axis)
                pattern_input.quantity = adsk.core.ValueInput.createByReal(count)
                pattern_input.totalAngle = adsk.core.ValueInput.createByReal(math.radians(angle))
                patterns.add(pattern_input)
                self.log(f"Created circular pattern: {count} instances")
        except Exception as e:
            self.log(f"Circular pattern failed: {str(e)}")
    
    def create_linear_pattern(self, operation):
        """Create linear pattern of features"""
        try:
            count = int(operation.get('count', 3))
            spacing = float(operation.get('spacing', 10.0)) / 10.0  # mm to cm
            direction = operation.get('direction', 'X')
            
            # Get the last feature to pattern
            if self.root_comp.features.count > 0:
                features = adsk.core.ObjectCollection.create()
                features.add(self.root_comp.features.item(self.root_comp.features.count - 1))
                
                # Use appropriate axis
                if direction == 'X':
                    axis = self.root_comp.xConstructionAxis
                elif direction == 'Y':
                    axis = self.root_comp.yConstructionAxis
                else:
                    axis = self.root_comp.zConstructionAxis
                
                patterns = self.root_comp.features.rectangularPatternFeatures
                pattern_input = patterns.createInput(features, axis, 
                    adsk.core.ValueInput.createByReal(count),
                    adsk.core.ValueInput.createByReal(spacing),
                    adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
                patterns.add(pattern_input)
                self.log(f"Created linear pattern: {count} instances")
        except Exception as e:
            self.log(f"Linear pattern failed: {str(e)}")
    
    def create_shell(self, operation):
        """Hollow out body with shell operation"""
        try:
            thickness = float(operation.get('thickness', 2.0)) / 10.0  # mm to cm
            
            # Get the body
            if self.root_comp.bRepBodies.count > 0:
                body = self.root_comp.bRepBodies.item(self.root_comp.bRepBodies.count - 1)
                
                # Get top face to remove (simplified - removes largest face in Z)
                faces_to_remove = adsk.core.ObjectCollection.create()
                max_z = -999999
                top_face = None
                for face in body.faces:
                    bbox = face.boundingBox
                    if bbox.maxPoint.z > max_z:
                        max_z = bbox.maxPoint.z
                        top_face = face
                
                if top_face:
                    faces_to_remove.add(top_face)
                    
                    shells = self.root_comp.features.shellFeatures
                    shell_input = shells.createInput(faces_to_remove, False)
                    shell_input.insideThickness = adsk.core.ValueInput.createByReal(thickness)
                    shells.add(shell_input)
                    self.log(f"Created shell with {thickness*10:.1f}mm wall thickness")
        except Exception as e:
            self.log(f"Shell operation failed: {str(e)}")
    
    def create_hole(self, operation):
        """Create a simple hole using extrude cut (more robust)"""
        try:
            # Convert mm to cm
            diameter = float(operation.get('diameter', 5.0)) / 10.0
            center = operation.get('center', [0, 0])
            plane_name = operation.get('plane', 'XY')
            
            self.log(f"Hole: Creating hole D={diameter*10:.1f}mm at {center}")
            
            if plane_name == 'XY':
                plane = self.root_comp.xYConstructionPlane
            elif plane_name == 'XZ':
                plane = self.root_comp.xZConstructionPlane
            elif plane_name == 'YZ':
                plane = self.root_comp.yZConstructionPlane
            else:
                plane = self.root_comp.xYConstructionPlane
            
            # Check if we have bodies to cut
            if self.root_comp.bRepBodies.count == 0:
                self.log("Hole: No bodies found to cut through", level='ERROR')
                return
                
            # Create sketch for hole
            sketch = self.root_comp.sketches.add(plane)
            circles = sketch.sketchCurves.sketchCircles
            center_point = adsk.core.Point3D.create(float(center[0])/10.0, float(center[1])/10.0, 0)
            circles.addByCenterRadius(center_point, diameter/2.0)
            
            self.log(f"Hole: Sketch created with circle profile")
            
            # Extrude cut
            profile = sketch.profiles.item(0)
            extrudes = self.root_comp.features.extrudeFeatures
            ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
            
            depth = operation.get('depth', 'through')
            if depth == 'through':
                # Use a large distance instead of setAllExtent for more reliable cutting
                distance = adsk.core.ValueInput.createByReal(100.0)  # 100cm = 1000mm
                ext_input.setDistanceExtent(False, distance)
                self.log("Hole: Using through-all (1000mm depth)")
            else:
                ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(float(depth)/10.0))
                self.log(f"Hole: Using depth {depth}mm")
            
            self.log(f"Hole: Executing extrude cut...")
            extrude_feature = extrudes.add(ext_input)
            
            if extrude_feature:
                self.log(f"Hole: Created successfully")
            else:
                self.log("Hole: Failed to create", level='ERROR')
        except Exception as e:
            self.log(f"Hole operation failed: {str(e)}", level='ERROR')
            import traceback
            self.log(traceback.format_exc())

    def create_combine(self, operation):
        """Combine bodies using boolean operations (union, cut, intersect)"""
        try:
            operation_type = operation.get('operation', 'join').lower()
            target_body_index = operation.get('target_body', 0)
            tool_body_index = operation.get('tool_body', 1)
            keep_tools = operation.get('keep_tools', False)
            
            self.log(f"Combine: Operation={operation_type}, target={target_body_index}, tool={tool_body_index}")
            
            # Check if we have enough bodies
            if self.root_comp.bRepBodies.count < 2:
                self.log(f"Combine: Need at least 2 bodies, found {self.root_comp.bRepBodies.count}", level='ERROR')
                return
            
            # Get bodies
            target_body = self.root_comp.bRepBodies.item(target_body_index)
            tool_body = self.root_comp.bRepBodies.item(tool_body_index)
            
            # Create combine feature
            combines = self.root_comp.features.combineFeatures
            combine_input = combines.createInput(target_body, adsk.core.ObjectCollection.create())
            combine_input.toolBodies.add(tool_body)
            combine_input.isKeepToolBodies = keep_tools
            
            # Set operation type
            if operation_type == 'join' or operation_type == 'union':
                combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
                self.log("Combine: Using JOIN operation")
            elif operation_type == 'cut' or operation_type == 'subtract':
                combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                self.log("Combine: Using CUT operation")
            elif operation_type == 'intersect' or operation_type == 'intersection':
                combine_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
                self.log("Combine: Using INTERSECT operation")
            else:
                self.log(f"Combine: Unknown operation type: {operation_type}", level='ERROR')
                return
            
            self.log("Combine: Executing combine...")
            combine_feature = combines.add(combine_input)
            
            if combine_feature:
                self.log(f"Combine: Successfully combined bodies")
            else:
                self.log("Combine: Failed to combine", level='ERROR')
                
        except Exception as e:
            self.log(f"Combine operation failed: {str(e)}", level='ERROR')
            import traceback
            self.log(traceback.format_exc())

    def create_fillet(self, operation):
        """Create a fillet on edges"""
        try:
            radius = float(operation.get('radius', 1.0)) / 10.0
            edges_selector = operation.get('edges', 'all')
            
            # Get the body created by the last feature
            if self.root_comp.bRepBodies.count == 0:
                self.log("No body found for fillet")
                return
                
            body = self.root_comp.bRepBodies.item(self.root_comp.bRepBodies.count - 1)
            
            edge_collection = adsk.core.ObjectCollection.create()
            
            for edge in body.edges:
                # Simple selection logic for now
                if edges_selector == 'all_outer_vertical':
                    # Select vertical edges that are not part of the inner corner
                    if abs(edge.startVertex.geometry.z - edge.endVertex.geometry.z) > 0.1:
                        edge_collection.add(edge)
                elif edges_selector == 'all':
                    # Only add edges that are suitable for filleting (not too small)
                    if edge.length > 0.01:  # Skip very small edges
                        edge_collection.add(edge)
            
            if edge_collection.count > 0:
                fillets = self.root_comp.features.filletFeatures
                fillet_input = fillets.createInput()
                fillet_input.addConstantRadiusEdgeSet(edge_collection, adsk.core.ValueInput.createByReal(radius), True)
                fillets.add(fillet_input)
                self.log(f"Applied fillet to {edge_collection.count} edges")
        except Exception as e:
            self.log(f"Fillet operation failed: {str(e)}")

    def create_chamfer(self, operation):
        """Create a chamfer on edges"""
        try:
            distance = float(operation.get('distance', 1.0)) / 10.0
            
            # Get the body created by the last feature
            if self.root_comp.bRepBodies.count == 0:
                self.log("No body found for chamfer")
                return
                
            body = self.root_comp.bRepBodies.item(self.root_comp.bRepBodies.count - 1)
            
            edge_collection = adsk.core.ObjectCollection.create()
            for edge in body.edges:
                # Only add edges that are suitable for chamfering (not too small)
                if edge.length > 0.01:  # Skip very small edges
                    edge_collection.add(edge)
                 
            if edge_collection.count > 0:
                chamfers = self.root_comp.features.chamferFeatures
                chamfer_input = chamfers.createInput(edge_collection, True)
                chamfer_input.setToEqualDistance(adsk.core.ValueInput.createByReal(distance))
                chamfers.add(chamfer_input)
                self.log(f"Applied chamfer to {edge_collection.count} edges")
        except Exception as e:
            self.log(f"Chamfer operation failed: {str(e)}")
    
    def export_model(self, task_id, export_format):
        """Export the model in the specified format"""
        export_mgr = self.design.exportManager
        
        if export_format == 'stl':
            filename = os.path.join(EXPORTS_DIR, f"{task_id}.stl")
            stl_options = export_mgr.createSTLExportOptions(self.root_comp)
            stl_options.filename = filename
            stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
            export_mgr.execute(stl_options)
            return filename
        elif export_format == 'f3d':
            filename = os.path.join(EXPORTS_DIR, f"{task_id}.f3d")
            options = export_mgr.createFusionArchiveExportOptions(filename, self.root_comp)
            export_mgr.execute(options)
            return filename
        else:
            raise ValueError(f"Unknown export format: {export_format}")
    
    def gather_metadata(self):
        """Gather metadata about the created model"""
        metadata = {
            'vertex_count': 0,
            'face_count': 0,
            'volume_cm3': 0.0,
            'surface_area_cm2': 0.0,
            'bounding_box': {'x': 0, 'y': 0, 'z': 0},
            'body_count': self.root_comp.bRepBodies.count
        }
        
        try:
            min_pt = [float('inf'), float('inf'), float('inf')]
            max_pt = [float('-inf'), float('-inf'), float('-inf')]
            has_bodies = False
            
            for body in self.root_comp.bRepBodies:
                has_bodies = True
                
                # Mesh stats
                try:
                    mesh_mgr = body.meshManager
                    mesh = mesh_mgr.displayMeshes.item(0)
                    if mesh:
                        metadata['vertex_count'] += mesh.nodeCount
                        metadata['face_count'] += mesh.triangleCount
                except:
                    pass
                
                # Physical properties
                try:
                    props = body.physicalProperties
                    metadata['volume_cm3'] += props.volume
                    metadata['surface_area_cm2'] += props.area
                except:
                    pass
                
                # Bounding box
                try:
                    bbox = body.boundingBox
                    min_pt[0] = min(min_pt[0], bbox.minPoint.x)
                    min_pt[1] = min(min_pt[1], bbox.minPoint.y)
                    min_pt[2] = min(min_pt[2], bbox.minPoint.z)
                    max_pt[0] = max(max_pt[0], bbox.maxPoint.x)
                    max_pt[1] = max(max_pt[1], bbox.maxPoint.y)
                    max_pt[2] = max(max_pt[2], bbox.maxPoint.z)
                except:
                    pass
            
            if has_bodies:
                metadata['bounding_box'] = {
                    'x': max_pt[0] - min_pt[0],
                    'y': max_pt[1] - min_pt[1],
                    'z': max_pt[2] - min_pt[2]
                }
                
        except Exception as e:
            self.log(f"Metadata error: {str(e)}")
        
        return metadata
    
    def create_component(self, operation):
        """Create a new component (occurrence)"""
        name = operation.get('name', 'Component')
        
        # Create new component in the root assembly
        transform = adsk.core.Matrix3D.create()
        occurrence = self.design.rootComponent.occurrences.addNewComponent(transform)
        occurrence.component.name = name
        
        # Set as active component for subsequent operations
        self.root_comp = occurrence.component
        self.log(f"Created component: {name}")
        
    def activate_component(self, operation):
        """Set a component as active by name"""
        name = operation.get('name')
        
        if name == 'root':
            self.root_comp = self.design.rootComponent
            self.log(f"Activated root component")
            return
            
        # Find component by name
        found = False
        for occ in self.design.rootComponent.occurrences:
            if occ.component.name == name:
                self.root_comp = occ.component
                found = True
                self.log(f"Activated component: {name}")
                break
        
        if not found:
            raise ValueError(f"Component not found: {name}")

    def create_joint(self, operation):
        """Create a joint between two components"""
        comp1_name = operation.get('component_1')
        comp2_name = operation.get('component_2')
        joint_type = operation.get('joint_type', 'rigid')
        
        # Find occurrences
        occ1 = None
        occ2 = None
        
        for occ in self.design.rootComponent.occurrences:
            if occ.component.name == comp1_name:
                occ1 = occ
            elif occ.component.name == comp2_name:
                occ2 = occ
        
        if not occ1 or not occ2:
            raise ValueError(f"Components not found for joint: {comp1_name}, {comp2_name}")
            
        # Create joint origins at component origins
        geo1 = adsk.fusion.JointGeometry.createByPoint(occ1.component.originConstructionPoint)
        geo2 = adsk.fusion.JointGeometry.createByPoint(occ2.component.originConstructionPoint)
        
        joints = self.design.rootComponent.joints
        joint_input = joints.createInput(geo1, geo2)
        
        # Set joint type
        if joint_type == 'rigid':
            joint_input.setAsRigidJointMotion()
        elif joint_type == 'revolute':
            joint_input.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type == 'slider':
            joint_input.setAsSliderJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        
        # Enable snap - this makes components position automatically
        joint_input.isFlipped = False
        
        joints.add(joint_input)
        self.log(f"Created {joint_type} joint between {comp1_name} and {comp2_name}")
    
    def transform_component(self, operation):
        """Move/rotate a component"""
        name = operation.get('name')
        offset = operation.get('offset', [0, 0, 0])  # [x, y, z] in cm
        
        # Find occurrence
        occ = None
        for o in self.design.rootComponent.occurrences:
            if o.component.name == name:
                occ = o
                break
        
        if not occ:
            raise ValueError(f"Component not found: {name}")
        
        # Create transform matrix
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(
            float(offset[0]) / 10.0,  # Convert mm to cm
            float(offset[1]) / 10.0,
            float(offset[2]) / 10.0
        )
        
        # Apply transform
        occ.transform = transform
        self.log(f"Transformed {name} by offset {offset}")
    
    def check_interferences(self):
        """Check for interferences between components"""
        try:
            # Get all bodies from all occurrences
            bodies = adsk.core.ObjectCollection.create()
            
            for occ in self.design.rootComponent.occurrences:
                for body in occ.bRepBodies:
                    bodies.add(body)
            
            if bodies.count < 2:
                return 0
            
            # Analyze interferences
            results = self.design.rootComponent.analyzeInterference(bodies)
            
            count = len(results)
            
            if count > 0:
                self.log(f"⚠️ Found {count} interference(s)!", level='WARNING')
            
            return count
            
        except Exception as e:
            self.log(f"Interference check failed: {str(e)}", level='WARNING')
            return 0
