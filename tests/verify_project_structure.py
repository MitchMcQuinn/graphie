#!/usr/bin/env python3
import os
import sys
import requests
import time
import subprocess
import signal
import atexit

def check_directory_exists(directory):
    """Check if a directory exists in the project."""
    exists = os.path.isdir(directory)
    print(f"✓ Directory '{directory}' exists") if exists else print(f"✗ Directory '{directory}' does not exist")
    return exists

def check_file_exists(file_path):
    """Check if a file exists in the project."""
    exists = os.path.isfile(file_path)
    print(f"✓ File '{file_path}' exists") if exists else print(f"✗ File '{file_path}' does not exist")
    return exists

def check_app_running():
    """Check if the application is running on port 5001."""
    try:
        response = requests.get("http://localhost:5001", timeout=2)
        if response.status_code == 200:
            print("✓ Application is running on port 5001")
            return True
        else:
            print(f"✗ Application returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("✗ Application is not running on port 5001")
        return False

def start_app():
    """Start the application using the setup script."""
    print("Starting application...")
    process = subprocess.Popen(["./setup.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Register cleanup function to kill the process when the script exits
    def cleanup():
        if process.poll() is None:
            print("Terminating application...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    atexit.register(cleanup)
    
    # Wait for the app to start
    for _ in range(10):
        if check_app_running():
            return True
        time.sleep(2)
    
    print("Failed to start application within timeout")
    return False

def verify_project_structure():
    """Verify the project structure is correct."""
    print("\n=== Verifying Project Structure ===\n")
    
    # Check directories
    directories = ["docs", "examples", "tests", "tools", "utils", "templates", "static"]
    all_dirs_exist = all(check_directory_exists(d) for d in directories)
    
    # Check core files
    core_files = ["app.py", "engine.py", "fixed_engine.py", "setup.sh", "requirements.txt"]
    all_core_files_exist = all(check_file_exists(f) for f in core_files)
    
    # Check tool files
    tool_files = [
        "tools/check_and_clean_workflow.py",
        "tools/check_workflow_steps.py",
        "tools/fix_show_analysis_node.py",
        "tools/update_workflow_for_fixed_engine.py"
    ]
    all_tool_files_exist = all(check_file_exists(f) for f in tool_files)
    
    # Check documentation files
    doc_files = ["docs/MAINTENANCE_GUIDE.md"]
    all_doc_files_exist = all(check_file_exists(f) for f in doc_files)
    
    # Overall structure check
    if all_dirs_exist and all_core_files_exist and all_tool_files_exist and all_doc_files_exist:
        print("\n✓ Project structure verification passed")
        return True
    else:
        print("\n✗ Project structure verification failed")
        return False

def verify_application():
    """Verify the application can run properly."""
    print("\n=== Verifying Application ===\n")
    
    # Check if app is already running
    app_running = check_app_running()
    
    if not app_running:
        # Try to start the app
        app_running = start_app()
    
    if app_running:
        print("\n✓ Application verification passed")
        return True
    else:
        print("\n✗ Application verification failed")
        return False

def main():
    """Main function to run all verifications."""
    print("=== Project Structure and Application Verification ===")
    
    structure_ok = verify_project_structure()
    app_ok = verify_application()
    
    if structure_ok and app_ok:
        print("\n✓ All verifications passed!")
        return 0
    else:
        print("\n✗ Some verifications failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 