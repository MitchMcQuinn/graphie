#!/usr/bin/env python3
"""
Simple test script to verify if the Graphie application is running.
Makes a request to the server and reports the status.
"""

import requests
import time
import sys

def check_app_running(url="http://localhost:5001", max_retries=5, retry_delay=1):
    """Check if the application is running by making a request to the server."""
    print(f"Testing if application is running at {url}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"✓ Application is running! Status code: {response.status_code}")
                return True
            else:
                print(f"✗ Application returned unexpected status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}/{max_retries}: Connection failed ({str(e)})")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("✗ Max retries exceeded. Application does not appear to be running.")
                return False
    
    return False

if __name__ == "__main__":
    # Allow custom URL to be passed as command line argument
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001"
    
    if check_app_running(url):
        print("\nTo debug the application, you can try the following endpoints:")
        print("- /debug_workflow: Overview of workflow state")
        print("- /debug_variables: Variable availability information")
        print("- /stream_log: Real-time log streaming")
        print("\nUse the browser to test the full interface.")
        sys.exit(0)
    else:
        print("\nApplication does not appear to be running.")
        print("Check the console logs for errors.")
        sys.exit(1) 