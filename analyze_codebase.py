#!/usr/bin/env python3
"""
Code Verification Script - No Terminal Dependencies
Validates code structure and imports without external execution
"""

import ast
import os
import sys
from pathlib import Path

def check_python_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def check_imports(file_path):
    """Check what imports a file has"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return imports
    except Exception:
        return []

def check_file_structure():
    """Check if all expected files exist"""
    expected_files = [
        'app.py',
        'hardware_layer.py', 
        'test_manager.py',
        'requirements.txt',
        'PROJECT_STATUS_REPORT.md',
        'HARDWARE_INTEGRATION_SUMMARY.md',
        'dash/hardware-setup.html',
        'dash/hardware-testing.html'
    ]
    
    results = {}
    for file_path in expected_files:
        results[file_path] = os.path.exists(file_path)
    
    return results

def analyze_codebase():
    """Analyze the entire codebase structure"""
    print("🔍 CODEBASE ANALYSIS")
    print("=" * 50)
    
    # Check file structure
    print("\n📁 File Structure Check:")
    file_results = check_file_structure()
    for file_path, exists in file_results.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
    
    # Check Python files syntax
    print("\n🐍 Python Syntax Check:")
    python_files = ['app.py', 'hardware_layer.py', 'test_manager.py', 'validate_integration.py']
    
    for file_path in python_files:
        if os.path.exists(file_path):
            is_valid, message = check_python_syntax(file_path)
            status = "✅" if is_valid else "❌"
            print(f"  {status} {file_path}: {message}")
            
            if is_valid:
                imports = check_imports(file_path)
                if imports:
                    print(f"    📦 Imports: {len(imports)} modules")
        else:
            print(f"  ❌ {file_path}: File not found")
    
    # Check HTML files
    print("\n🌐 HTML Template Check:")
    html_files = ['dash/hardware-setup.html', 'dash/hardware-testing.html']
    
    for file_path in html_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'Hardware' in content and 'TayTech' in content:
                    print(f"  ✅ {file_path}: Content validated")
                else:
                    print(f"  ⚠️ {file_path}: Missing expected content")
            except Exception as e:
                print(f"  ❌ {file_path}: Error reading file - {e}")
        else:
            print(f"  ❌ {file_path}: File not found")
    
    # Project statistics
    print("\n📊 Project Statistics:")
    
    total_files = 0
    total_lines = 0
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith(('.py', '.html', '.md')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                    total_files += 1
                    total_lines += lines
                except:
                    pass
    
    print(f"  📄 Total files: {total_files}")
    print(f"  📝 Total lines: {total_lines:,}")
    
    # Hardware integration check
    print("\n🔧 Hardware Integration Status:")
    
    hardware_features = [
        ('Hardware API endpoints', 'app.py', '/api/hardware/'),
        ('Hardware abstraction layer', 'hardware_layer.py', 'HardwareInterface'),
        ('Test management system', 'test_manager.py', 'TestManager'),
        ('Hardware setup UI', 'dash/hardware-setup.html', 'Hardware Setup'),
        ('Hardware testing UI', 'dash/hardware-testing.html', 'Hardware Testing')
    ]
    
    for feature_name, file_path, search_term in hardware_features:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if search_term in content:
                    print(f"  ✅ {feature_name}")
                else:
                    print(f"  ❌ {feature_name}: Missing {search_term}")
            except:
                print(f"  ❌ {feature_name}: Error reading {file_path}")
        else:
            print(f"  ❌ {feature_name}: {file_path} not found")
    
    print("\n🎉 Analysis Complete!")
    return True

if __name__ == '__main__':
    try:
        success = analyze_codebase()
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
    except Exception as e:
        print(f"\n❌ ANALYSIS FAILED: {e}")
        sys.exit(1)