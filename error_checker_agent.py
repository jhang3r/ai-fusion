"""
Autonomous Error Checker Agent
Continuously monitors and validates all Python files in the project
Runs as a background watchdog to prevent code corruption
"""

import time
import os
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from code_validator import CodeValidator
from datetime import datetime


class ErrorCheckerAgent(FileSystemEventHandler):
    """Autonomous agent that monitors and validates all Python files"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.validator = CodeValidator(str(project_root))
        self.last_check = {}
        self.error_count = 0
        self.warning_count = 0
        
        print("🤖 Error Checker Agent initialized")
        print(f"📁 Monitoring: {self.project_root}")
        print("="*70)
        
        # Initial validation
        self.validate_all_files()
    
    def on_modified(self, event):
        """Called when a file is modified"""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.py'):
            return
        
        # Skip __pycache__ and other temp files
        if '__pycache__' in event.src_path or event.src_path.endswith('.pyc'):
            return
        
        self.validate_file(event.src_path)
    
    def on_created(self, event):
        """Called when a file is created"""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.py'):
            return
        
        print(f"\n📄 New file detected: {event.src_path}")
        self.validate_file(event.src_path)
    
    def validate_file(self, file_path: str):
        """Validate a single file and report results"""
        # Debounce - don't check same file within 1 second
        now = time.time()
        if file_path in self.last_check:
            if now - self.last_check[file_path] < 1.0:
                return
        
        self.last_check[file_path] = now
        
        print(f"\n🔍 Checking: {Path(file_path).name}")
        
        is_valid, errors, warnings = self.validator.validate_file(file_path)
        
        if is_valid:
            if warnings:
                print(f"  ⚠️  VALID with {len(warnings)} warning(s)")
                for warning in warnings:
                    print(f"     {warning}")
                self.warning_count += len(warnings)
            else:
                print(f"  ✅ VALID - No issues")
        else:
            print(f"  ❌ INVALID - {len(errors)} error(s)")
            for error in errors:
                print(f"     {error}")
            self.error_count += len(errors)
            
            # CRITICAL: Alert on corruption
            print("\n" + "!"*70)
            print("⚠️  CORRUPTION DETECTED!")
            print("!"*70)
            print(f"File: {file_path}")
            print("Action: Manual intervention required")
            print("Recommendation: Revert to last known good version")
            print("!"*70 + "\n")
    
    def validate_all_files(self):
        """Validate all Python files in project"""
        print("\n🔍 Running full project validation...")
        
        results = self.validator.validate_project()
        
        total_files = len(results)
        valid_files = sum(1 for is_valid, _, _ in results.values() if is_valid)
        invalid_files = total_files - valid_files
        
        total_errors = sum(len(errors) for _, errors, _ in results.values())
        total_warnings = sum(len(warnings) for _, _, warnings in results.values())
        
        print(f"\n📊 Validation Summary:")
        print(f"   Files checked: {total_files}")
        print(f"   ✅ Valid: {valid_files}")
        print(f"   ❌ Invalid: {invalid_files}")
        print(f"   ⚠️  Warnings: {total_warnings}")
        
        if invalid_files > 0:
            print(f"\n❌ ERRORS FOUND ({total_errors} total):")
            for file_path, (is_valid, errors, warnings) in results.items():
                if not is_valid:
                    print(f"\n  {Path(file_path).name}:")
                    for error in errors:
                        print(f"    • {error}")
        
        self.error_count = total_errors
        self.warning_count = total_warnings
        
        print("="*70)
        print(f"🤖 Agent ready - monitoring for changes...")
        print("="*70 + "\n")
    
    def print_status(self):
        """Print current status"""
        print(f"\n📊 Agent Status [{datetime.now().strftime('%H:%M:%S')}]:")
        print(f"   Total errors detected: {self.error_count}")
        print(f"   Total warnings: {self.warning_count}")
        print(f"   Files monitored: {len(self.last_check)}")


def run_agent(project_root: str = None):
    """Run the error checker agent"""
    if project_root is None:
        project_root = os.getcwd()
    
    # Create agent
    agent = ErrorCheckerAgent(project_root)
    
    # Set up file system observer
    observer = Observer()
    observer.schedule(agent, str(agent.project_root), recursive=True)
    observer.start()
    
    print("Press Ctrl+C to stop the agent\n")
    
    try:
        while True:
            time.sleep(30)  # Print status every 30 seconds
            agent.print_status()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping Error Checker Agent...")
        observer.stop()
    
    observer.join()
    print("✅ Agent stopped")


if __name__ == '__main__':
    # Check if watchdog is installed
    try:
        import watchdog
    except ImportError:
        print("❌ Error: 'watchdog' package not installed")
        print("Install with: pip install watchdog")
        sys.exit(1)
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else None
    run_agent(project_root)
