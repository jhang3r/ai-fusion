# Fusion 360 AI Interface API Reference

This document lists all supported commands, operations, and parameters for the Fusion 360 AI training system.

## Task Structure

```json
{
  "task_id": "unique_id_string",
  "type": "create_part",
  "description": "Human readable description",
  "operations": [ ... list of operations ... ],
  "export_formats": ["stl", "step", "f3d"]
}
```

## Operations

### 1. Sketch (`sketch`)
Creates a 2D sketch on a plane or face.

**Parameters:**
- `plane`: Target plane.
  - Standard: `"XY"`, `"XZ"`, `"YZ"`
  - Faces: `"top_face"`, `"front_face"`, `"right_face"` (requires existing body)
- `offset`: (Optional) Distance to offset plane from origin/face.
- `geometry`: Type of geometry to draw.

**Geometry Types:**

#### `rectangle`
- `width`: float
- `height`: float
- `center`: [x, y]

#### `circle`
- `radius`: float
- `center`: [x, y]

#### `line`
- `start`: [x, y]
- `end`: [x, y]

#### `gear_profile`
- `teeth`: int
- `module`: float
- `bore`: float (optional)

#### `multi`
Allows multiple geometry items in one sketch.
- `items`: List of geometry objects (each having `type` and `params`).
  - Supported types: `rectangle`, `circle`, `line`, `gear_profile`

---

### 2. Extrude (`extrude`)
Extrudes the last created sketch.

**Parameters:**
- `distance`: float (mm)
- `operation`:
  - `"new_body"` (default)
  - `"join"`
  - `"cut"`
  - `"intersect"`

---

### 3. Revolve (`revolve`)
Revolves the last created sketch around an axis.

**Parameters:**
- `angle`: float (degrees, default 360)
- `axis`: `"X"`, `"Y"`, `"Z"` (currently defaults to Z axis of sketch plane in some contexts, needs explicit support)

---

### 4. Fillet (`fillet`)
Rounds sharp edges.

**Parameters:**
- `radius`: float (mm)
- `edges`:
  - `"all"`: All edges of the first body.
  - `"last"`: (Planned) Edges of the last feature.

---

### 5. Chamfer (`chamfer`)
Bevels sharp edges.

**Parameters:**
- `distance`: float (mm)
- `edges`:
  - `"all"`: All edges of the first body.

---

## Assembly Operations

### `create_component`
Creates a new empty component (occurrence) in the assembly.
- `name`: string

### `activate_component`
Sets a component as the active target for new operations.
- `name`: string

### `create_joint`
Joins two components together. Components automatically snap to align at their origins.
- `component_1`: string
- `component_2`: string
- `joint_type`: `"rigid"`, `"revolute"`, `"slider"`

### `transform_component`
Moves a component to a specific position.
- `name`: string (component name)
- `offset`: [x, y, z] (mm)

---

## Export Formats
- `"stl"`: STL mesh file
- `"step"`: STEP CAD file
- `"f3d"`: Fusion 360 Archive (preserves full parametric history and assemblies)

---

## Assembly Features
- **Automatic positioning**: Joints snap components together at their origins
- **Interference detection**: Automatically checks for overlapping components
- **Connection points**: Semantic metadata for intelligent assembly (in development)
