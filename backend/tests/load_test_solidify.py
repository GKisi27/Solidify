# Load Testing Script for Solidify
# Place in: backend/tests/load_test_solidify.py

"""
Locust load testing script for Solidify multi-user simulation.

Usage:
    pip install locust
    locust -f backend/tests/load_test_solidify.py --host=http://localhost:8000
    
    Open browser: http://localhost:8089
    Configure: 10 users, spawn rate 1/sec
"""

import random
import io
from locust import HttpUser, task, between
from PIL import Image

class SolidifyUser(HttpUser):
    """Simulates a Solidify user performing conversion workflows."""
    
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts. Login once per user."""
        user_num = random.randint(1, 100)
        self.username = f"user{user_num}"
        self.password = f"password{user_num}"
        
        # Login
        response = self.client.post("/auth/login", data={
            "username": self.username,
            "password": self.password
        }, name="/auth/login")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user_id")
            print(f"✅ User {self.username} logged in (user_id={self.user_id})")
        else:
            print(f"⚠️  User {self.username} login failed")
            self.token = None
            self.user_id = None
    
    def _create_test_image(self):
        """Generate a test PNG image in memory."""
        img = Image.new('RGB', (200, 200), color=(73, 109, 137))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    
    @task(5)  # 50% of requests - Upload and convert
    def upload_and_convert(self):
        """Upload an image and start conversion."""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        files = {
            "file": ("test_image.png", self._create_test_image(), "image/png")
        }
        
        with self.client.post(
            "/files/convert",
            files=files,
            headers=headers,
            catch_response=True,
            name="/files/convert"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("task_id")
                backend = data.get("backend", "unknown")
                
                if task_id:
                    self.task_id = task_id
                    response.success()
                else:
                    response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(3)  # 30% of requests - Check task status
    def check_task_status(self):
        """Poll task status."""
        if not self.token or not hasattr(self, 'task_id'):
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        with self.client.get(
            f"/files/task/{self.task_id}",
            headers=headers,
            catch_response=True,
            name="/files/task/:id"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                ready = data.get("ready", False)
                response.success()
                
                if ready:
                    history_id = data.get("history_id")
                    if history_id:
                        self.history_id = history_id
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(2)  # 20% of requests - Get results
    def get_results(self):
        """Fetch conversion results."""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        if hasattr(self, 'history_id'):
            params = {"history_id": self.history_id}
        else:
            params = {"user_id": self.user_id}
        
        with self.client.get(
            "/files/results",
            params=params,
            headers=headers,
            catch_response=True,
            name="/files/results"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


if __name__ == "__main__":
    print("Load Test Script for Solidify")
    print("=" * 70)
    print("To run:")
    print("  1. Ensure Solidify is running: make dev")
    print("  2. Install Locust: pip install locust")
    print("  3. Run: locust -f backend/tests/load_test_solidify.py --host=http://localhost:8000")
    print("  4. Open browser: http://localhost:8089")
    print("=" * 70)
