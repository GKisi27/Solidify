"""
Load testing for multiple concurrent users using Locust
No server initialization needed - Locust creates its own test environment

Installation:
    pip install locust

Running:
    locust -f tests/load_test.py --host=http://localhost:8000 -u 100 -r 10 -t 60s

Or for headless testing:
    locust -f tests/load_test.py --host=http://localhost:8000 -u 50 -r 5 -t 30s --headless
"""

from locust import HttpUser, task, between, TaskSet, events
import json
from datetime import datetime


class UserBehavior(TaskSet):
    """Defines user behavior/tasks"""
    
    access_token = None
    user_id = None
    
    @task(1)
    def login(self):
        """Simulate user login"""
        username = f"user_{self.user.client.pool_manager.connection_pool_kw.get('username', 'test')}"
        password = "test_password"
        
        with self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_id = data.get("user_id")
                response.success()
            else:
                response.failure(f"Login failed with status {response.status_code}")
    
    @task(2)
    def health_check(self):
        """Simulate health check request"""
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        } if self.access_token else {}
        
        with self.client.get(
            "/health",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def get_history(self):
        """Simulate getting user history"""
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        } if self.access_token else {}
        
        with self.client.get(
            "/history",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"History endpoint failed: {response.status_code}")


class SolidifyUser(HttpUser):
    """Represents a real user accessing the Solidify app"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    tasks = [UserBehavior]


# Event handlers for test statistics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*60)
    print(f"⏱️  STARTING LOAD TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print(f"✅ TEST COMPLETED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Print summary
    print("\n📊 TEST SUMMARY:")
    print("-" * 60)
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Success rate: {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")


# Event handler for request completion
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    if exception:
        print(f"❌ {request_type} {name}: {exception}")
    else:
        print(f"✅ {request_type} {name}: {response.status_code} ({response_time:.0f}ms)")
