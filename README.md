# Fusion 360 AI Training System

A training system that enables AI to practice parametric CAD modeling in Fusion 360, with real-time feedback for iterative improvement. Designed for creating complex mechanical designs for sci-fi entertainment (video games, movies).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Training Orchestrator                      │
│  (Generates tasks, analyzes results, provides feedback)      │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ├─ Write task.json               ├─ Read result.json
             │                                │
        ┌────▼────────────────────────────────▼────┐
        │         Shared Directory                 │
        │  tasks/ | results/ | exports/            │
        └────┬────────────────────────────────┬────┘
             │                                │
             ├─ Read task                     ├─ Write result
             │                                │
        ┌────▼────────────────────────────────▼────┐
        │      Fusion 360 Interface Script         │
        │  (Executes CAD operations, exports STL)  │
        └──────────────────────────────────────────┘
                         │
                         ├─ Analyze mesh
                         │
                    ┌────▼────┐
                    │ STL File│
                    └─────────┘
```

## Components

### 1. **fusion360_interface.py**
Runs inside Fusion 360. Monitors for task files, executes CAD operations, exports models.

**Installation:**
1. Open Fusion 360
2. Go to `Tools > Add-Ins > Scripts and Add-Ins`
3. Click green "+" next to "My Scripts"
4. Navigate to `fusion360_interface.py`
5. Click "Run"

### 2. **training_orchestrator.py**
External Python application that manages the training loop.

**Features:**
- Generates design tasks with varying difficulty
- Submits tasks to Fusion 360
- Waits for completion
- Analyzes exported models
- Provides detailed feedback
- Tracks progress over time

### 3. **feedback_analyzer.py**
Analyzes 3D mesh quality and provides actionable feedback.

**Metrics:**
- Mesh quality (vertex count, face count, manifold check)
- Dimensional accuracy (compare to specifications)
- Topology analysis (Euler characteristic, genus)
- Geometric properties (volume, surface area, bounding box)

### 4. **design_primitives.py**
Library of reusable design operation templates.

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Fusion 360 script:**
   - Follow instructions in Component #1 above

3. **Create directory structure:**
   ```
   ai-fusion/
   ├── shared/
   │   ├── tasks/
   │   ├── results/
   │   └── exports/
   ├── training_data/
   │   └── sessions/
   ├── curriculum/
   └── references/
   ```

## Usage

### Test Mode (Single Task)
```bash
python training_orchestrator.py --test-mode simple_cylinder
```

### Full Training Session
```bash
python training_orchestrator.py
```

### Analyze Existing Model
```bash
python feedback_analyzer.py model.stl [target_x] [target_y] [target_z]
```

## Training Curriculum

### Level 1: Basic Shapes
- Simple cylinders
- Rectangular boxes
- Spheres

**Goal:** Learn basic sketch and extrude operations

### Level 2: Mechanical Components
- Gears and sprockets
- Bolts and fasteners
- Bearing housings
- Shafts

**Goal:** Master multi-operation parts with precise dimensions

### Level 3: Assemblies
- Multiple components
- Joints and constraints
- Motion studies

**Goal:** Understand component relationships and constraints

### Level 4: Sci-Fi Props
- Weapons (pistols, rifles)
- Devices (scanners, communicators)
- Vehicle components (panels, engines)

**Goal:** Create detailed, aesthetically pleasing designs

## Feedback System

The system provides three types of feedback:

### 1. **Quantitative Metrics**
- Dimensional accuracy (% deviation from spec)
- Mesh quality score (0-100)
- Topology efficiency

### 2. **Qualitative Analysis**
- Visual comparison to references
- Style consistency
- Detail level appropriateness

### 3. **Actionable Suggestions**
- Specific parameter adjustments
- Design improvements
- Best practices

## Example Workflow

1. **Orchestrator generates task:**
   ```json
   {
     "task_id": "task_0001",
     "description": "Create a cylinder Ø20mm × 30mm",
     "operations": [...]
   }
   ```

2. **Fusion 360 executes task:**
   - Creates sketch
   - Extrudes profile
   - Exports STL

3. **Analyzer provides feedback:**
   ```
   Overall Score: 85/100
   
   ✅ STRENGTHS:
      ✓ Mesh is watertight
      ✓ X: 20.1mm (target: 20mm, deviation: 0.5%)
   
   ⚠️ ISSUES:
      ⚠ Z: 31.5mm (target: 30mm, deviation: 5%)
   
   💡 SUGGESTIONS:
      • Adjust Z dimension - currently off by 5%
   ```

4. **Next iteration improves based on feedback**

## Progress Tracking

Progress is saved in `training_data/progress.json`:
```json
{
  "current_level": 1,
  "completed_tasks": 42,
  "total_score": 3567.5,
  "best_scores": {
    "simple_cylinder": 95.2,
    "gear": 87.3
  }
}
```

## File Formats

### Task File
JSON file with design instructions and parameters

### Result File
JSON file with execution results and metadata

### Export Formats
- **STL**: For mesh analysis
- **STEP**: For CAD interchange
- **F3D**: Native Fusion 360 format

## Tips for Success

1. **Start Simple:** Begin with basic shapes before complex assemblies
2. **Review Feedback:** Carefully read suggestions and adjust accordingly
3. **Iterate:** Don't expect perfection on first try - learning takes practice
4. **Track Progress:** Monitor your scores to see improvement over time
5. **Reference Images:** Use concept art as visual targets for sci-fi props

## Troubleshooting

**Fusion 360 script not responding:**
- Check that script is running (green indicator)
- Verify shared directory paths are correct
- Look for error messages in Fusion 360 UI

**Timeout waiting for results:**
- Complex operations may take longer
- Increase timeout in orchestrator
- Check Fusion 360 isn't showing error dialogs

**Mesh analysis errors:**
- Ensure STL export completed successfully
- Check file isn't corrupted
- Verify trimesh can load the file

## Future Enhancements

- [ ] Visual comparison with reference images
- [ ] Automated rendering for aesthetic evaluation
- [ ] Multi-component assembly support
- [ ] Advanced surface modeling operations
- [ ] Material and appearance evaluation
- [ ] Integration with rendering engines

## License

MIT License - Feel free to modify and extend!
