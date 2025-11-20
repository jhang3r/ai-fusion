"""
Comprehensive Code Validator
Validates Python files for syntax errors, imports, and basic structural integrity
"""

import ast
import os
import sys
from pathlib import Path
from typing import Tuple, List, Dict


class CodeValidator:
    """Validates Python code for syntax and structural integrity"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single Python file
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False, self.errors, self.warnings
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            self.errors.append(f"Failed to read file: {str(e)}")
            return False, self.errors, self.warnings
        
        # Check 1: Syntax validation
        if not self._check_syntax(code, str(file_path)):
            return False, self.errors, self.warnings
        
        # Check 2: AST validation
        if not self._check_ast(code, str(file_path)):
            return False, self.errors, self.warnings
        
        # Check 3: Import validation
        self._check_imports(code, file_path)
        
        # Check 4: Basic structure validation
        self._check_structure(code)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _check_syntax(self, code: str, filename: str) -> bool:
        """Check for syntax errors"""
        try:
            compile(code, filename, 'exec')
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            if e.text:
                self.errors.append(f"  {e.text.strip()}")
            return False
        except Exception as e:
            self.errors.append(f"Compilation error: {str(e)}")
            return False
    
    def _check_ast(self, code: str, filename: str) -> bool:
        """Check AST structure"""
        try:
            tree = ast.parse(code, filename)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Check for undefined names in function calls
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    # This is a basic check - could be expanded
                    pass
                
                # Check for incomplete statements
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name):
                    if hasattr(node, 'lineno'):
                        self.warnings.append(f"Line {node.lineno}: Statement has no effect")
            
            return True
        except SyntaxError as e:
            self.errors.append(f"AST parse error at line {e.lineno}: {e.msg}")
            return False
        except Exception as e:
            self.errors.append(f"AST validation error: {str(e)}")
            return False
    
    def _check_imports(self, code: str, file_path: Path):
        """Check import statements"""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Check if module exists (basic check)
                        try:
                            __import__(alias.name.split('.')[0])
                        except ImportError:
                            # Only warn for non-project imports
                            if not alias.name.startswith('adsk'):  # Fusion 360 modules
                                self.warnings.append(f"Import '{alias.name}' may not be available")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        try:
                            __import__(node.module.split('.')[0])
                        except ImportError:
                            if not node.module.startswith('adsk'):
                                self.warnings.append(f"Module '{node.module}' may not be available")
        
        except Exception as e:
            self.warnings.append(f"Import check failed: {str(e)}")
    
    def _check_structure(self, code: str):
        """Check basic code structure"""
        try:
            tree = ast.parse(code)
            
            # Check for functions/classes with no body
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if len(node.body) == 0:
                        self.warnings.append(f"Empty {node.__class__.__name__}: {node.name}")
                    elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        self.warnings.append(f"{node.__class__.__name__} '{node.name}' only contains 'pass'")
        
        except Exception as e:
            self.warnings.append(f"Structure check failed: {str(e)}")
    
    def validate_project(self, exclude_dirs: List[str] = None) -> Dict[str, Tuple[bool, List[str], List[str]]]:
        """
        Validate all Python files in the project
        
        Returns:
            Dict mapping file paths to (is_valid, errors, warnings)
        """
        if exclude_dirs is None:
            exclude_dirs = ['__pycache__', '.git', 'venv', 'env', '.venv']
        
        results = {}
        
        for py_file in self.project_root.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            
            is_valid, errors, warnings = self.validate_file(str(py_file))
            results[str(py_file)] = (is_valid, errors, warnings)
        
        return results
    
    def print_validation_report(self, results: Dict[str, Tuple[bool, List[str], List[str]]]):
        """Print a formatted validation report"""
        total_files = len(results)
        valid_files = sum(1 for is_valid, _, _ in results.values() if is_valid)
        invalid_files = total_files - valid_files
        
        print("\n" + "="*70)
        print("CODE VALIDATION REPORT")
        print("="*70)
        print(f"\nTotal files checked: {total_files}")
        print(f"✓ Valid: {valid_files}")
        print(f"✗ Invalid: {invalid_files}")
        
        if invalid_files > 0:
            print("\n" + "-"*70)
            print("ERRORS:")
            print("-"*70)
            for file_path, (is_valid, errors, warnings) in results.items():
                if not is_valid:
                    print(f"\n{file_path}:")
                    for error in errors:
                        print(f"  ✗ {error}")
        
        # Show warnings
        total_warnings = sum(len(warnings) for _, _, warnings in results.values())
        if total_warnings > 0:
            print("\n" + "-"*70)
            print(f"WARNINGS ({total_warnings} total):")
            print("-"*70)
            for file_path, (is_valid, errors, warnings) in results.items():
                if warnings:
                    print(f"\n{file_path}:")
                    for warning in warnings:
                        print(f"  ⚠ {warning}")
        
        print("\n" + "="*70)


def validate_code_integrity(file_path: str = None, project_root: str = None) -> bool:
    """
    Quick validation function for single file or entire project
    
    Args:
        file_path: Path to single file to validate (optional)
        project_root: Root directory of project (optional, defaults to current dir)
    
    Returns:
        True if all files are valid, False otherwise
    """
    if project_root is None:
        project_root = os.getcwd()
    
    validator = CodeValidator(project_root)
    
    if file_path:
        is_valid, errors, warnings = validator.validate_file(file_path)
        if not is_valid:
            print(f"\n✗ Validation failed for {file_path}:")
            for error in errors:
                print(f"  {error}")
        return is_valid
    else:
        results = validator.validate_project()
        validator.print_validation_report(results)
        return all(is_valid for is_valid, _, _ in results.values())


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Validate specific file
        file_path = sys.argv[1]
        is_valid = validate_code_integrity(file_path)
        sys.exit(0 if is_valid else 1)
    else:
        # Validate entire project
        is_valid = validate_code_integrity()
        sys.exit(0 if is_valid else 1)
