import requests
from typing import List, Dict
import json
from mac_monitor import EnhancedMacMonitor
from datetime import datetime  # Add this import


class EnhancedMacMonitorClient(EnhancedMacMonitor):
    def __init__(self, api_url: str, api_token: str, batch_size: int = 60):
        """
        Initialize the monitor with API configuration
        
        :param api_url: Base URL of your Laravel API (e.g., 'http://localhost:8000/api')
        :param api_token: Bearer token for API authentication
        :param batch_size: Number of records to batch before sending to API
        """
        super().__init__(db_path="activity_detailed.db")
        self.api_url = api_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.batch_size = batch_size
        self.current_batch: List[Dict] = []

    def send_batch_to_api(self):
        """Send the current batch of logs to the API"""
        if not self.current_batch:
            return

        try:
            response = requests.post(
                f'{self.api_url}/activity-logs',
                headers=self.headers,
                json={'logs': self.current_batch}
            )
            response.raise_for_status()
            print(f"\nSuccessfully sent {len(self.current_batch)} logs to API")
            self.current_batch = []
        except requests.exceptions.RequestException as e:
            print(f"\nError sending logs to API: {e}")

    def log_activity(self, window_info: Dict[str, str], system_info: Dict):
        """Override log_activity to send data to API instead of SQLite"""
        log_entry = {
            'log_timestamp': datetime.now().isoformat(),
            'window_title': window_info['window_title'],
            'application': window_info['application'],
            'cpu_percent': system_info['cpu_percent'],
            'memory_percent': system_info['memory_percent'],
            'battery_percent': system_info['battery_percent'],
            'is_charging': system_info['is_charging'],
            'active_process_count': system_info['active_process_count'],
            'network_bytes_sent': system_info['network_bytes_sent'],
            'network_bytes_recv': system_info['network_bytes_recv'],
            'screen_resolution': system_info['screen_resolution'],
            'idle_time': system_info['idle_time']
        }

        self.current_batch.append(log_entry)

        if len(self.current_batch) >= self.batch_size:
            self.send_batch_to_api()

    def monitor(self, interval: int = 5):
        """Override monitor method to ensure final batch is sent"""
        try:
            super().monitor(interval)
        finally:
            if self.current_batch:
                self.send_batch_to_api()

if __name__ == "__main__":
    # Configuration for local testing
    API_URL = "http://localhost:8000/api"
    API_TOKEN = "1|HzRZKQ6sHPQ4L5S19IYRqndeIIiOAs9KYv57ZNxq2967b218"  # Get this from your Laravel application
    
    monitor = EnhancedMacMonitorClient(API_URL, API_TOKEN)
    monitor.monitor()