# Testing Instructions for Fusion 360 AI Training System

## Step 1: Install Fusion 360 Script

1. **Open Fusion 360**

2. **Open Scripts and Add-Ins Dialog:**
   - Press `Shift + S`, OR
   - Go to `Tools > Add-Ins > Scripts and Add-Ins`

3. **Add the Script:**
   - Click the **Scripts** tab
   - Click the green **"+"** button next to "My Scripts"
   - Navigate to: `c:\Users\jrdnh\Documents\ai-fusion\fusion360_interface.py`
   - Click **OK**

4. **Run the Script:**
   - Select `fusion360_interface` from the list
   - Click **Run**
   - You should see a message: "Fusion 360 AI Training Interface Started!"

**⚠️ IMPORTANT:** Keep Fusion 360 open with the script running during testing!

---

## Step 2: Run Test Task (From Command Line)

Open a **new terminal/PowerShell** window and run:

```bash
cd c:\Users\jrdnh\Documents\ai-fusion
python training_orchestrator.py --test-mode simple_cylinder
```

**What should happen:**

1. Orchestrator generates a cylinder task
2. Writes task file to `shared/tasks/`
3. Fusion 360 script detects the task
4. Creates a cylinder in Fusion 360
5. Exports STL to `shared/exports/`
6. Writes result to `shared/results/`
7. Orchestrator analyzes the STL
8. Prints detailed feedback

---

## Expected Output

```
🧪 Test Mode: Running single simple_cylinder task

✓ Task submitted: task_YYYYMMDD_HHMMSS_0001
  Description: Create a cylinder with diameter 20.0mm and height 30.0mm

⏳ Waiting for Fusion 360 to complete task...
✓ Task completed in 2.3s

======================================================================
FEEDBACK REPORT
======================================================================

📊 Overall Score: 85.0/100

✅ STRENGTHS:
   ✓ Mesh is watertight (no holes)
   ✓ Mesh has consistent winding (manifold)
   ✓ Good vertex count: 1520
   ✓ X: 20.1mm (target: 20mm, deviation: 0.5%)

⚠️  ISSUES:
   ⚠ Z: 31.5mm (target: 30mm, deviation: 5%)

💡 SUGGESTIONS:
   • Adjust Z dimension - currently off by 5%

======================================================================
```

---

## Troubleshooting

### Issue: "Timeout waiting for task completion"

**Possible causes:**
- Fusion 360 script not running
- Script crashed with an error
- Task file path incorrect

**Solutions:**
1. Check Fusion 360 for error dialog boxes
2. Look at the Fusion 360 script output panel
3. Verify `shared/tasks/` directory exists
4. Restart the Fusion 360 script

### Issue: Fusion 360 Script Shows Errors

**Common API errors and fixes:**

1. **"Module not found: adsk"**
   - This is normal - the script must run INSIDE Fusion 360
   - Don't try to run it from command line

2. **"Cannot access property X"**
   - API syntax may need adjustment
   - Copy the exact error message
   - We'll fix the script based on the error

3. **"File path not found"**
   - The script uses `Path(__file__).parent` to find directories
   - May need to use absolute paths instead

### Issue: STL Export Fails

**Possible causes:**
- No geometry created
- Export path doesn't exist
- Permissions issue

**Solutions:**
1. Check if cylinder was actually created in Fusion 360
2. Verify `shared/exports/` directory exists
3. Try exporting manually to test permissions

---

## What to Report

If there are errors, please provide:

1. **Exact error message** from Fusion 360
2. **Which step failed** (task detection, geometry creation, export, etc.)
3. **Any dialog boxes** that appeared
4. **Console output** from the Python script

---

## Next Steps After Successful Test

Once the test works:

1. **Run multiple tasks:**
   ```bash
   python training_orchestrator.py
   ```

2. **Check progress:**
   ```bash
   python session_manager.py
   ```

3. **Generate charts:**
   ```bash
   python progress_tracker.py --charts
   ```

4. **Start actual training** and iterate to improve scores!

---

## Quick Reference

**Start Fusion 360 script:**
- Fusion 360 > Tools > Scripts and Add-Ins > Run fusion360_interface

**Run single test:**
```bash
python training_orchestrator.py --test-mode simple_cylinder
```

**Run training session:**
```bash
python training_orchestrator.py
```

**View progress:**
```bash
python session_manager.py
```

**Generate charts:**
```bash
python progress_tracker.py --charts
```
