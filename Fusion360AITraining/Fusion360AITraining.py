"""
Fusion 360 Interface Script - Hot Reload Loader
This script stays running and automatically reloads the task processor module when it changes.
"""

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import json
import os
import time
import threading
import importlib
import sys

# Global variables
app = None
ui = None
handlers = []
stop_flag = False
my_custom_event = 'Fusion360AITraining_TaskEvent'
custom_event = None

# Configuration
BASE_DIR = r"c:\Users\jrdnh\Documents\ai-fusion"
SHARED_DIR = os.path.join(BASE_DIR, "shared")
TASKS_DIR = os.path.join(SHARED_DIR, "tasks")
RESULTS_DIR = os.path.join(SHARED_DIR, "results")
EXPORTS_DIR = os.path.join(SHARED_DIR, "exports")
SCRIPT_DIR = os.path.join(BASE_DIR, "Fusion360AITraining")

# Ensure directories exist
for directory in [SHARED_DIR, TASKS_DIR, RESULTS_DIR, EXPORTS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Add script directory to path for imports
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Import the task processor module
import fusion_task_processor

# Set the directory paths in the module
fusion_task_processor.RESULTS_DIR = RESULTS_DIR
fusion_task_processor.EXPORTS_DIR = EXPORTS_DIR
fusion_task_processor.LOG_FILE = os.path.join(SHARED_DIR, "fusion_logs.jsonl")

# Track last modification time
last_mod_time = 0


def log_message(message):
    """Log message to Text Commands palette"""
    global ui
    try:
        palette = ui.palettes.itemById('TextCommands')
        if palette:
            if not palette.isVisible:
                palette.isVisible = True
            palette.writeText(message)
    except:
        pass


def validate_module(module_path):
    """Validate Python module for syntax errors before loading"""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, module_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def check_and_reload_module():
    """Check if module has changed and reload if valid"""
    global last_mod_time
    
    module_path = os.path.join(SCRIPT_DIR, "fusion_task_processor.py")
    
    try:
        current_mod_time = os.path.getmtime(module_path)
        
        if current_mod_time > last_mod_time:
            # File has changed - validate before reloading
            is_valid, error = validate_module(module_path)
            
            if is_valid:
                importlib.reload(fusion_task_processor)
                last_mod_time = current_mod_time
                
                # CRITICAL: Validate AFTER reload to catch any corruption
                is_valid_after, error_after = validate_module(module_path)
                if not is_valid_after:
                    log_message(f"✗ CORRUPTION DETECTED after reload!")
                    log_message(f"  Error: {error_after}")
                    log_message("  ROLLING BACK - keeping previous version")
                    # Don't update paths - keep old version active
                    return
                
                log_message(f"✓ Reloaded fusion_task_processor.py")
                
                # Update directory paths after reload
                fusion_task_processor.RESULTS_DIR = RESULTS_DIR
                fusion_task_processor.EXPORTS_DIR = EXPORTS_DIR
                fusion_task_processor.LOG_FILE = os.path.join(SHARED_DIR, "fusion_logs.jsonl")
            else:
                log_message(f"✗ Reload REJECTED - {error}")
                log_message("  Previous version still active")
    except Exception as e:
        log_message(f"Reload check failed: {str(e)}")


class ThreadEventHandler(adsk.core.CustomEventHandler):
    """Handles the custom event fired from the background thread"""
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        global app, ui
        try:
            # Get the file path passed in the event arguments
            event_args = adsk.core.CustomEventArgs.cast(args)
            if not event_args:
                return
                
            data = json.loads(event_args.additionalInfo)
            task_file = data.get('file')
            
            if task_file and os.path.exists(task_file):
                # Check for module updates before processing task
                check_and_reload_module()
                
                # Create processor instance and run task
                processor = fusion_task_processor.TaskProcessor(app, ui)
                processor.process_task_file(task_file)
                
        except:
            if ui:
                ui.messageBox('Failed in event handler:\n{}'.format(traceback.format_exc()))


# Background thread to monitor for tasks and file changes
def monitor_tasks_and_files():
    """Background thread that checks for tasks and module changes"""
    global stop_flag, app, custom_event, last_mod_time
    
    # Initialize last mod time
    module_path = os.path.join(SCRIPT_DIR, "fusion_task_processor.py")
    try:
        last_mod_time = os.path.getmtime(module_path)
    except:
        pass
    
    while not stop_flag:
        try:
            # Check for module updates every iteration
            check_and_reload_module()
            
            # Check for tasks
            task_files = [os.path.join(TASKS_DIR, f) for f in os.listdir(TASKS_DIR) 
                         if (f.startswith('task_') or f.startswith('test_')) and f.endswith('.json')]
            
            if task_files:
                task_files.sort()
                task_file = task_files[0]
                
                # Fire event to process on main thread
                if custom_event:
                    app.fireCustomEvent(my_custom_event, json.dumps({'file': task_file}))
                    
                    # Wait a bit to prevent firing multiple times for same file
                    time.sleep(2)
            
        except:
            pass
        time.sleep(1)  # Check every second


def run(context):
    """Main entry point for the script"""
    global app, ui, stop_flag, custom_event
    
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Prevent script from terminating automatically
        adsk.autoTerminate(False)
        
        # Register custom event
        try:
            app.unregisterCustomEvent(my_custom_event)
        except:
            pass
            
        custom_event = app.registerCustomEvent(my_custom_event)
        on_thread_event = ThreadEventHandler()
        custom_event.add(on_thread_event)
        handlers.append(on_thread_event)
        
        stop_flag = False
        
        # Start background monitoring thread
        monitor_thread = threading.Thread(target=monitor_tasks_and_files)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        ui.messageBox(f'Fusion 360 AI Training Interface Started!\n\n' +
                     f'Monitoring: {TASKS_DIR}\n' +
                     f'Hot Reload: ENABLED\n\n' +
                     f'Edit fusion_task_processor.py and changes will reload automatically.\n\n' +
                     f'Running in background. Use "Stop" button to stop.')
        
    except:
        error_msg = traceback.format_exc()
        if ui:
            ui.messageBox('Failed:\n{}'.format(error_msg))
        
        # Write error to file for orchestrator to see
        try:
            error_file = os.path.join(SHARED_DIR, "fusion_error.txt")
            with open(error_file, 'w') as f:
                f.write(error_msg)
        except:
            pass


def stop(context):
    """Called when the script is stopped"""
    global ui, stop_flag, app
    
    stop_flag = True
    
    try:
        if app:
            app.unregisterCustomEvent(my_custom_event)
            
        if ui:
            ui.messageBox('Fusion 360 AI Training Interface Stopped')
    except:
        pass
