# Quick Start Guide - Fusion 360 AI Training System

## What This System Does

This system allows an AI (like me, Gemini) to **practice and learn** parametric CAD modeling in Fusion 360. Through iterative feedback, the AI improves at creating mechanical designs for sci-fi entertainment.

**Key Point:** The AI learns in-context through practice and feedback - no model fine-tuning required!

## How It Works

```
1. AI generates design instructions
   ↓
2. Fusion 360 executes the design
   ↓
3. Model is exported and analyzed
   ↓
4. AI receives detailed feedback
   ↓
5. AI adjusts and tries again (LEARNING!)
```

## Installation (5 minutes)

### Step 1: Install Python Dependencies
```bash
cd c:\Users\jrdnh\Documents\ai-fusion
pip install -r requirements.txt
```

### Step 2: Set Up Fusion 360 Script
1. Open Fusion 360
2. Press `Shift + S` (or go to Tools > Add-Ins > Scripts and Add-Ins)
3. Click the **Scripts** tab
4. Click the green **"+"** button next to "My Scripts"
5. Navigate to: `c:\Users\jrdnh\Documents\ai-fusion\fusion360_interface.py`
6. Select it and click **OK**
7. Click **Run** to start the interface

You should see a message: "Fusion 360 AI Training Interface Started!"

### Step 3: Verify Setup
```bash
python training_orchestrator.py --test-mode simple_cylinder
```

This will:
- Generate a simple cylinder task
- Submit it to Fusion 360
- Wait for completion
- Analyze the result
- Show feedback

## Usage

### Test Mode (Single Task)
Perfect for testing or practicing one specific thing:

```bash
# Test a cylinder
python training_orchestrator.py --test-mode simple_cylinder

# Test a box
python training_orchestrator.py --test-mode simple_box

# Test a gear
python training_orchestrator.py --test-mode gear
```

### Full Training Session
Run multiple tasks automatically:

```bash
python training_orchestrator.py
```

This will run 10 random tasks from: cylinders, boxes, and gears.

### Resume After Context Reset

When starting a new conversation, first check your progress:

```bash
python session_manager.py
```

This shows:
- Total tasks completed
- Average score
- Best scores by task type
- Recent performance trends
- Recommendations

### Export Learning Summary

Create a comprehensive summary to review:

```bash
python session_manager.py --export
```

This creates `training_data/learning_summary.md` with:
- All session history
- Detailed feedback from each task
- Key learnings and patterns

## Understanding Feedback

### Score Breakdown
- **90-100**: Excellent - ready for more complex tasks
- **80-89**: Good - minor improvements needed
- **70-79**: Acceptable - review suggestions carefully
- **Below 70**: Needs work - focus on fundamentals

### Feedback Categories

**✅ STRENGTHS** - What you did well
```
✓ Mesh is watertight (no holes)
✓ X: 20.1mm (target: 20mm, deviation: 0.5%)
```

**⚠️ ISSUES** - What went wrong
```
⚠ Z: 31.5mm (target: 30mm, deviation: 5%)
✗ Mesh has holes - not watertight
```

**💡 SUGGESTIONS** - How to improve
```
• Adjust Z dimension - currently off by 5%
• Ensure all sketches are closed profiles before extruding
```

## Training Progression

### Level 1: Basic Shapes (Start Here!)
- Simple cylinders
- Rectangular boxes
- Spheres

**Goal:** Master basic operations, achieve 80+ average score

### Level 2: Mechanical Components
- Gears
- Bolts
- Bearing housings

**Goal:** Multi-operation parts, 85+ average score

### Level 3: Assemblies
- Multiple components
- Joints and constraints

**Goal:** Component relationships, 85+ average score

### Level 4: Sci-Fi Props
- Weapons
- Devices
- Vehicle components

**Goal:** Production-ready assets, 85+ average score

## Context Reset Strategy

**Problem:** When the conversation context fills up or restarts, I lose memory.

**Solution:** All learning is persisted to disk!

### When Starting a New Session:

1. **Check Progress:**
   ```bash
   python session_manager.py
   ```

2. **Review Learning Summary:**
   ```bash
   python session_manager.py --export
   # Then read: training_data/learning_summary.md
   ```

3. **Continue Training:**
   ```bash
   python training_orchestrator.py
   ```

The system automatically:
- Loads previous progress
- Continues from current level
- Tracks improvement over time

## Troubleshooting

### "Timeout waiting for task completion"
- **Cause:** Fusion 360 script not running or task failed
- **Fix:** Check Fusion 360 for error dialogs, restart the script

### "STL file not found"
- **Cause:** Export failed
- **Fix:** Check Fusion 360 export settings, verify shared/exports/ directory exists

### "Module not found" errors
- **Cause:** Python dependencies not installed
- **Fix:** Run `pip install -r requirements.txt`

### Fusion 360 script shows errors
- **Cause:** Invalid task operations
- **Fix:** Check task JSON format, review Fusion 360 API documentation

## Tips for Success

1. **Start Simple:** Begin with Level 1 tasks (cylinders, boxes)
2. **Read Feedback Carefully:** Every suggestion helps you improve
3. **Iterate:** Don't expect perfection - learning takes practice
4. **Track Progress:** Review session_manager.py output regularly
5. **Save Learning Summaries:** Export summaries before context resets

## File Structure

```
ai-fusion/
├── fusion360_interface.py          # Runs in Fusion 360
├── training_orchestrator.py        # Main training loop
├── feedback_analyzer.py            # Analyzes models
├── session_manager.py              # Handles context continuity
├── design_primitives.py            # Design templates
├── shared/                         # Communication directory
│   ├── tasks/                      # Task queue
│   ├── results/                    # Results
│   └── exports/                    # Exported models (STL/STEP)
├── training_data/                  # Persistent learning data
│   ├── progress.json               # Overall progress
│   ├── learning_summary.md         # Exported summary
│   └── sessions/                   # Detailed session logs
└── curriculum/                     # Training levels
    ├── 01_basic_shapes.json
    ├── 02_mechanical_parts.json
    └── 04_scifi_props.json
```

## Next Steps

1. **Install and test** the system (see Installation above)
2. **Run a test task** to verify everything works
3. **Start Level 1 training** with basic shapes
4. **Review feedback** and iterate
5. **Export summaries** periodically for context continuity

## Questions?

- Check `README.md` for detailed documentation
- Review curriculum files for learning objectives
- Examine session logs in `training_data/sessions/` for examples

---

**Remember:** This system is designed for the AI to learn through practice, just like a human would. The key is iteration and feedback!
