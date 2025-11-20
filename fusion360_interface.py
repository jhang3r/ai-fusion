"""
Fusion 360 Interface Script
Runs inside Fusion 360 to receive design tasks and execute CAD operations.

Installation:
1. Open Fusion 360
2. Go to Tools > Add-Ins > Scripts and Add-Ins
3. Click the green "+" next to "My Scripts"
4. Navigate to this file and select it
5. Click "Run" to start monitoring for tasks

This script will continuously monitor the shared/tasks directory for new task files.
"""

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import json
import os
import time
import math
from pathlib import Path

# Global variables
app = None
ui = None
handlers = []

# Configuration
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR / "shared"
TASKS_DIR = SHARED_DIR / "tasks"
RESULTS_DIR = SHARED_DIR / "results"
EXPORTS_DIR = SHARED_DIR / "exports"

# Ensure directories exist
for directory in [SHARED_DIR, TASKS_DIR, RESULTS_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class TaskProcessor:
    """Processes design tasks from JSON files"""
    
    def __init__(self, app, ui):
        self.app = app
        self.ui = ui
        self.design = None
        self.root_comp = None
        
    def process_task_file(self, task_file):
        """Process a single task file"""
        try:
            # Read task
            with open(task_file, 'r') as f:
                task = json.load(f)
            
            task_id = task['task_id']
            self.ui.messageBox(f"Processing task: {task_id}")
            
            # Create new document
            doc = self.app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            self.design = adsk.fusion.Design.cast(self.app.activeProduct)
            self.root_comp = self.design.rootComponent
            
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
                    exports[export_format] = str(export_path)
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
            
            result_file = RESULTS_DIR / f"result_{task_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Delete task file to mark as processed
            task_file.unlink()
            
            self.ui.messageBox(f"Task {task_id} completed!")
            
        except Exception as e:
            self.ui.messageBox(f"Error processing task: {str(e)}\n{traceback.format_exc()}")
    
    def execute_operation(self, operation):
        """Execute a single CAD operation"""
        op_type = operation['type']
        
        if op_type == 'sketch':
            self.create_sketch(operation)
        elif op_type == 'extrude':
            self.create_extrude(operation)
        elif op_type == 'revolve':
            self.create_revolve(operation)
        elif op_type == 'hole':
            self.create_hole(operation)
        elif op_type == 'fillet':
            self.create_fillet(operation)
        elif op_type == 'chamfer':
            self.create_chamfer(operation)
        elif op_type == 'create_component':
            self.create_component(operation)
        elif op_type == 'activate_component':
            self.activate_component(operation)
        elif op_type == 'create_joint':
            self.create_joint(operation)
        else:
            raise ValueError(f"Unknown operation type: {op_type}")

    def create_component(self, operation):
        """Create a new component (occurrence)"""
        name = operation.get('name', 'Component')
        
        # Create new component in the root assembly
        transform = adsk.core.Matrix3D.create()
        occurrence = self.design.rootComponent.occurrences.addNewComponent(transform)
        occurrence.component.name = name
        
        # Set as active component for subsequent operations
        self.root_comp = occurrence.component
        
    def activate_component(self, operation):
        """Set a component as active by name"""
        name = operation.get('name')
        
        if name == 'root':
            self.root_comp = self.design.rootComponent
            return
            
        # Find component by name
        # This is a simple search, might need to be recursive for nested assemblies
        found = False
        for occ in self.design.rootComponent.occurrences:
            if occ.component.name == name:
                self.root_comp = occ.component
                found = True
                break
        
        if not found:
            # If not found, stay on current or default to root? 
            # For now, raise error to be safe
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
            
        # Create geometry input (simplified - using origin for now)
        # Real implementation needs specific geometry selection (faces, edges)
        geo1 = adsk.fusion.JointGeometry.createByPoint(occ1.component.originConstructionPoint)
        geo2 = adsk.fusion.JointGeometry.createByPoint(occ2.component.originConstructionPoint)
        
        joints = self.design.rootComponent.joints
        joint_input = joints.createInput(geo1, geo2)
        
        # Set joint type
        if joint_type == 'rigid':
            joint_input.setAsRigidJointMotion()
        elif joint_type == 'revolute':
            # Default to Z axis
            joint_input.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type == 'slider':
            joint_input.setAsSliderJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
            
        joints.add(joint_input)
    
    def create_sketch(self, operation):
        """Create a sketch with geometry"""
        # Get or create sketch plane
        plane_name = operation.get('plane', 'XY')
        
        if plane_name == 'XY':
            plane = self.root_comp.xYConstructionPlane
        elif plane_name == 'XZ':
            plane = self.root_comp.xZConstructionPlane
        elif plane_name == 'YZ':
            plane = self.root_comp.yZConstructionPlane
        elif plane_name in ['top_face', 'front_face', 'right_face']:
            plane = self.get_face_by_name(plane_name)
            if not plane:
                # Fallback to XY if no body exists yet
                plane = self.root_comp.xYConstructionPlane
        else:
            raise ValueError(f"Unknown plane: {plane_name}")
        
        sketch = self.root_comp.sketches.add(plane)
    
    def get_face_by_name(self, name):
        """Find a face on the existing body by name/orientation"""
        if self.root_comp.bRepBodies.count == 0:
            return None
            
        body = self.root_comp.bRepBodies[0]
        
        best_face = None
        max_val = -float('inf')
        
        for face in body.faces:
            # Skip non-planar faces for sketches
            if face.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                continue
                
            centroid = face.centroid
            
            if name == 'top_face':
                # Max Z
                if centroid.z > max_val:
                    max_val = centroid.z
                    best_face = face
            elif name == 'front_face':
                # Max Y (assuming Y is forward/back)
                if centroid.y > max_val:
                    max_val = centroid.y
                    best_face = face
            elif name == 'right_face':
                # Max X
                if centroid.x > max_val:
                    max_val = centroid.x
                    best_face = face
                    
        return best_face
        
        # Create geometry based on type
        geometry_type = operation.get('geometry', 'rectangle')
        params = operation.get('params', {})
        
        if geometry_type == 'rectangle':
            self.sketch_rectangle(sketch, params)
        elif geometry_type == 'circle':
            self.sketch_circle(sketch, params)
        elif geometry_type == 'gear_profile':
            self.sketch_gear(sketch, params)
        elif geometry_type == 'multi':
            for item in operation.get('items', []):
                item_type = item.get('type')
                item_params = item.get('params', {})
                
                if item_type == 'rectangle':
                    self.sketch_rectangle(sketch, item_params)
                elif item_type == 'circle':
                    self.sketch_circle(sketch, item_params)
                elif item_type == 'gear_profile':
                    self.sketch_gear(sketch, item_params)
                elif item_type == 'line':
                    self.sketch_line(sketch, item_params)
                elif item_type == 'fillet_sketch':
                    self.sketch_fillet(sketch, item_params)
        else:
            raise ValueError(f"Unknown geometry type: {geometry_type}")
        
        return sketch
    
    def sketch_rectangle(self, sketch, params):
        """Draw a rectangle"""
        width = params.get('width', 10.0)
        height = params.get('height', 10.0)
        
        lines = sketch.sketchCurves.sketchLines
        point0 = adsk.core.Point3D.create(-width/2, -height/2, 0)
        point1 = adsk.core.Point3D.create(width/2, -height/2, 0)
        point2 = adsk.core.Point3D.create(width/2, height/2, 0)
        point3 = adsk.core.Point3D.create(-width/2, height/2, 0)
        
        lines.addByTwoPoints(point0, point1)
        lines.addByTwoPoints(point1, point2)
        lines.addByTwoPoints(point2, point3)
        lines.addByTwoPoints(point3, point0)
    
    def sketch_circle(self, sketch, params):
        """Draw a circle"""
        radius = params.get('radius', 5.0)
        center = params.get('center', [0, 0])
        
        circles = sketch.sketchCurves.sketchCircles
        center_point = adsk.core.Point3D.create(center[0], center[1], 0)
        circles.addByCenterRadius(center_point, radius)
    
    def sketch_line(self, sketch, params):
        """Draw a line"""
        start = params.get('start', [0, 0])
        end = params.get('end', [10, 0])
        
        lines = sketch.sketchCurves.sketchLines
        p1 = adsk.core.Point3D.create(start[0], start[1], 0)
        p2 = adsk.core.Point3D.create(end[0], end[1], 0)
        lines.addByTwoPoints(p1, p2)

    def sketch_fillet(self, sketch, params):
        """Create a fillet in sketch (simplified/placeholder)"""
        # Real sketch fillet requires finding the lines at the vertex
        # This is complex to implement reliably without object IDs
        # For now, we'll skip it to prevent crashing, or just log it
        pass

    def sketch_gear(self, sketch, params):
        """Draw a simplified gear profile"""
        teeth = params.get('teeth', 20)
        module = params.get('module', 2.0)
        
        # Simplified gear calculation
        pitch_diameter = module * teeth
        outer_diameter = pitch_diameter + (2 * module)
        root_diameter = pitch_diameter - (2.5 * module)
        
        # Draw outer circle (simplified - real gears need involute curves)
        circles = sketch.sketchCurves.sketchCircles
        center = adsk.core.Point3D.create(0, 0, 0)
        circles.addByCenterRadius(center, outer_diameter / 2)
        circles.addByCenterRadius(center, root_diameter / 2)
    
    def create_extrude(self, operation):
        """Create an extrusion"""
        # Get the profile (last sketch created)
        # For multi-profile sketches, we might want to use all profiles
        # But for now, let's try to use all profiles in the sketch
        sketch = self.root_comp.sketches[-1]
        
        distance = operation.get('distance', 10.0)
        operation_type = operation.get('operation', 'new_body')
        
        extrudes = self.root_comp.features.extrudeFeatures
        
        # Create a collection of profiles
        profiles = adsk.core.ObjectCollection.create()
        for profile in sketch.profiles:
            profiles.add(profile)
            
        # Determine operation type
        op_enum = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        if operation_type == 'cut':
            op_enum = adsk.fusion.FeatureOperations.CutFeatureOperation
        elif operation_type == 'join':
            op_enum = adsk.fusion.FeatureOperations.JoinFeatureOperation
        elif operation_type == 'intersect':
            op_enum = adsk.fusion.FeatureOperations.IntersectFeatureOperation
            
        ext_input = extrudes.createInput(profiles, op_enum)
        
        distance_value = adsk.core.ValueInput.createByReal(distance)
        ext_input.setDistanceExtent(False, distance_value)
        
        extrudes.add(ext_input)
    
    def create_revolve(self, operation):
        """Create a revolve feature"""
        profile = self.root_comp.sketches[-1].profiles[0]
        
        # Get axis (simplified - using Z axis)
        axis = self.root_comp.zConstructionAxis
        
        revolves = self.root_comp.features.revolveFeatures
        rev_input = revolves.createInput(profile, axis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        angle = operation.get('angle', 360.0)
        angle_value = adsk.core.ValueInput.createByReal(math.radians(angle))
        rev_input.setAngleExtent(False, angle_value)
        
        revolves.add(rev_input)
    
    def create_hole(self, operation):
        """Create a hole"""
        # This is simplified - real implementation would need face selection
        pass
    
    def create_fillet(self, operation):
        """Create a fillet"""
        radius = operation.get('radius', 1.0)
        edges_scope = operation.get('edges', 'all')
        
        fillets = self.root_comp.features.filletFeatures
        edge_collection = adsk.core.ObjectCollection.create()
        
        if edges_scope == 'all':
            # Add all edges from the first body
            if self.root_comp.bRepBodies.count > 0:
                body = self.root_comp.bRepBodies[0]
                for edge in body.edges:
                    edge_collection.add(edge)
        elif edges_scope == 'last':
            # Add edges from the last feature
            # This is tricky, but we can try to get edges from the last feature
            pass
            
        if edge_collection.count > 0:
            fillet_input = fillets.createInput()
            fillet_input.addConstantRadiusEdgeSet(edge_collection, adsk.core.ValueInput.createByReal(radius), True)
            fillets.add(fillet_input)
    
    def create_chamfer(self, operation):
        """Create a chamfer"""
        distance = operation.get('distance', 1.0)
        edges_scope = operation.get('edges', 'all')
        
        chamfers = self.root_comp.features.chamferFeatures
        edge_collection = adsk.core.ObjectCollection.create()
        
        if edges_scope == 'all':
            # Add all edges from the first body
            if self.root_comp.bRepBodies.count > 0:
                body = self.root_comp.bRepBodies[0]
                for edge in body.edges:
                    edge_collection.add(edge)
                    
        if edge_collection.count > 0:
            chamfer_input = chamfers.createInput(edge_collection, True)
            chamfer_input.setToEqualDistance(adsk.core.ValueInput.createByReal(distance))
            chamfers.add(chamfer_input)
    
    def export_model(self, task_id, export_format):
        """Export the model in the specified format"""
        export_mgr = self.design.exportManager
        
        if export_format == 'stl':
            filename = EXPORTS_DIR / f"{task_id}.stl"
            stl_options = export_mgr.createSTLExportOptions(self.root_comp)
            stl_options.filename = str(filename)
            stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
            export_mgr.execute(stl_options)
            return filename
            
        elif export_format == 'step':
            filename = EXPORTS_DIR / f"{task_id}.step"
            step_options = export_mgr.createSTEPExportOptions(str(filename))
            export_mgr.execute(step_options)
            return filename
            
        elif export_format == 'f3d':
            filename = EXPORTS_DIR / f"{task_id}.f3d"
            options = export_mgr.createFusionArchiveExportOptions(str(filename), self.root_comp)
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
            'bounding_box': {'x': 0, 'y': 0, 'z': 0}
        }
        
        try:
            # Get physical properties
            if self.root_comp.bRepBodies.count > 0:
                body = self.root_comp.bRepBodies[0]
                
                # Get mesh statistics (approximate)
                mesh_mgr = body.meshManager
                mesh = mesh_mgr.displayMeshes.item(0)
                if mesh:
                    metadata['vertex_count'] = mesh.nodeCount
                    metadata['face_count'] = mesh.triangleCount
                
                # Get physical properties
                props = body.physicalProperties
                metadata['volume_cm3'] = props.volume
                metadata['surface_area_cm2'] = props.area
                
                # Get bounding box
                bbox = body.boundingBox
                metadata['bounding_box'] = {
                    'x': bbox.maxPoint.x - bbox.minPoint.x,
                    'y': bbox.maxPoint.y - bbox.minPoint.y,
                    'z': bbox.maxPoint.z - bbox.minPoint.z
                }
        except:
            pass
        
        return metadata


def run(context):
    """Main entry point for the script"""
    global app, ui
    
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        ui.messageBox('Fusion 360 AI Training Interface Started! (v1.1)\n\n'
                     f'Monitoring: {TASKS_DIR}\n\n'
                     'Place task JSON files in the tasks directory to begin.')
        
        processor = TaskProcessor(app, ui)
        
        # Monitor for task files
        while True:
            adsk.doEvents()
            task_files = list(TASKS_DIR.glob('task_*.json'))
            
            if task_files:
                # Process oldest task first
                task_files.sort()
                processor.process_task_file(task_files[0])
            
            time.sleep(1)  # Check every second
            
            
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    """Called when the script is stopped"""
    global ui
    
    try:
        if ui:
            ui.messageBox('Fusion 360 AI Training Interface Stopped')
    except:
        pass
