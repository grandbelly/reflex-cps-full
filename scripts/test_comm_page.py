"""
Test if communication page is accessible
"""

import requests
import time

def test_comm_page():
    """Test communication page accessibility"""
    
    # Wait a bit for the app to fully start
    time.sleep(5)
    
    try:
        # Test main page
        response = requests.get("http://localhost:13000", timeout=10)
        print(f"Main page status: {response.status_code}")
        
        # Test communication page
        response = requests.get("http://localhost:13000/comm", timeout=10)
        print(f"Communication page status: {response.status_code}")
        
        if response.status_code == 200:
            # Check if page contains expected elements
            content = response.text
            if "Communication Success Rate" in content:
                print("✓ Communication page title found")
            if "Select Sensor" in content:
                print("✓ Sensor selector found")
            if "Time Period" in content:
                print("✓ Time period selector found")
            if "heatmap" in content.lower():
                print("✓ Heatmap component found")
            
            print("\n✅ Communication monitoring page is working!")
        else:
            print(f"❌ Page returned status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing page: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_comm_page()