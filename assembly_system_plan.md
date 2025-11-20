# Fusion 360 AI Assembly System Plan

## Goal
Enable the AI to design and assemble multi-component systems where parts spatially fit together and interact (e.g., gears on shafts, pistons in cylinders).

## Core Concepts

### 1. Component-Based Architecture
Currently, we create bodies in the `rootComponent`. For assemblies, we must create new `Occurrences` (Components) for each part.

```python
# Create a new component
occurrence = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
component = occurrence.component
component.name = "Gear_1"
```

### 2. Connection Points (The "LEGO" Approach)
Instead of arbitrary geometry matching, we define explicit "Connection Points" (CPs) on parts. If CPs match, parts can be assembled.

**Types of Connection Points:**
- **`ThreadedHole`**: Size (M6), Pitch (1.0), Depth
- **`Bolt`**: Size (M6), Pitch (1.0), Length
- **`MountingPattern`**: Count (4), PCD (50mm), Hole Diameter (5mm)
- **`Shaft`**: Diameter (10mm), Keyway (3x3mm)
- **`Bore`**: Diameter (10mm), Keyway (3x3mm)

**Matching Logic:**
- `ThreadedHole(M6)` matches `Bolt(M6)`
- `Shaft(10mm)` matches `Bore(10mm)`
- `MountingPattern(4, 50mm)` matches `MountingPattern(4, 50mm)`

The AI's task becomes: "Find a part with a compatible Connection Point and align them."

### 3. Joints (The Glue)
We will expose Fusion's Joint API. The AI will specify:
- `component_1` + `geometry_1` (e.g., face, edge)
- `component_2` + `geometry_2`
- `joint_type` (Rigid, Revolute, Slider, Cylindrical)

```json
{
  "type": "create_joint",
  "joint_type": "revolute",
  "component_1": "Housing",
  "geometry_1": {"type": "face", "index": 5}, # Bearing seat
  "component_2": "Shaft",
  "geometry_2": {"type": "face", "index": 0}  # Shaft surface
}
```

## Proposed Workflow

1. **Generate Components**:
   - The AI generates `part_1.json`, `part_2.json`, etc.
   - Or a single `assembly.json` that defines multiple parts.

2. **Positioning**:
   - Parts are created at the origin.
   - We use `transform` operations to move them roughly into place (optional, as Joints can snap them).

3. **Joint Creation**:
   - The AI identifies the mating geometry.
   - The system creates the Joint, which snaps the parts together.

4. **Interference Checking**:
   - We use `rootComp.findInterferences()` to verify parts aren't overlapping invalidly.

## New Task Types

1. **`simple_assembly`**:
   - Create a Cube and a Cylinder.
   - Rigid Joint the Cylinder to the top of the Cube.

2. **`piston_assembly`**:
   - Create Cylinder Body (Housing).
   - Create Piston (Cylinder).
   - Slider Joint Piston inside Housing.

3. **`gear_train`**:
   - Create 2 Gears and a Base.
   - Revolute Joint both gears to Base at correct distance.

## Implementation Steps

1. **Update `fusion_task_processor.py`**:
   - Add `create_new_component()`
   - Add `activate_component()`
   - Add `create_joint()`

2. **Update `training_orchestrator.py`**:
   - Generate multi-part tasks.
   - Define target assembly relationships.

3. **Verification**:
   - Check `joint.isHealthy`.
   - Check `interference`.
