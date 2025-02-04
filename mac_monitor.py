import time
import datetime
import sqlite3
from typing import Dict
import subprocess
import pandas as pd
import psutil
import platform
from datetime import datetime
import json
from tabulate import tabulate
import os

class EnhancedMacMonitor:
    def __init__(self, db_path: str = "activity_detailed.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Drop existing table if it exists
        c.execute('DROP TABLE IF EXISTS activity_logs')
        
        # Create new table with expanded schema
        c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            timestamp TEXT,
            window_title TEXT,
            application TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            battery_percent REAL,
            is_charging INTEGER,
            active_process_count INTEGER,
            network_bytes_sent INTEGER,
            network_bytes_recv INTEGER,
            screen_resolution TEXT,
            idle_time INTEGER
        )''')
        
        conn.commit()
        conn.close()

    def get_active_window_info(self) -> Dict[str, str]:
        """Get information about the currently active window using AppleScript."""
        apple_script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            set windowTitle to ""
            try
                tell process frontApp
                    set windowTitle to name of front window
                end tell
            end try
            return {frontApp, windowTitle}
        end tell
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', apple_script], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                app_name, window_title = result.stdout.strip().split(',', 1)
                return {
                    'window_title': window_title.strip(),
                    'application': app_name.strip()
                }
            
        except Exception as e:
            print(f"Error getting window info: {e}")
            
        return {
            'window_title': 'unknown',
            'application': 'unknown'
        }

    def get_system_info(self):
        """Collect various system metrics."""
        # CPU and Memory
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Reduced interval to speed up data collection
        except:
            cpu_percent = 0
            
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
        except:
            memory_percent = 0
        
        # Battery information
        try:
            battery = psutil.sensors_battery()
            battery_percent = battery.percent if battery else 0
            is_charging = 1 if battery and battery.power_plugged else 0
        except:
            battery_percent = 0
            is_charging = 0
        
        # Process count
        try:
            active_process_count = len(list(psutil.process_iter()))
        except:
            active_process_count = 0
        
        # Network statistics
        try:
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent
            bytes_recv = network.bytes_recv
        except:
            bytes_sent = 0
            bytes_recv = 0
        
        # Screen resolution using AppleScript
        apple_script = '''
        tell application "Finder"
            set screenResolution to bounds of window of desktop
            return screenResolution
        end tell
        '''
        try:
            result = subprocess.run(['osascript', '-e', apple_script], 
                                 capture_output=True, text=True)
            screen_resolution = result.stdout.strip()
        except:
            screen_resolution = "unknown"
        
        # Get idle time using pmset
        try:
            idle_output = subprocess.check_output(['pmset', '-g', 'powerstate'], 
                                               stderr=subprocess.STDOUT).decode()
            idle_time = int(float(idle_output.split('\n')[1].split()[3]))
        except:
            idle_time = 0
            
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'battery_percent': battery_percent,
            'is_charging': is_charging,
            'active_process_count': active_process_count,
            'network_bytes_sent': bytes_sent,
            'network_bytes_recv': bytes_recv,
            'screen_resolution': screen_resolution,
            'idle_time': idle_time
        }

    def log_activity(self, window_info: Dict[str, str], system_info: Dict):
        """Log the activity with all metrics to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
        INSERT INTO activity_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            window_info['window_title'],
            window_info['application'],
            system_info['cpu_percent'],
            system_info['memory_percent'],
            system_info['battery_percent'],
            system_info['is_charging'],
            system_info['active_process_count'],
            system_info['network_bytes_sent'],
            system_info['network_bytes_recv'],
            system_info['screen_resolution'],
            system_info['idle_time']
        ))
        
        conn.commit()
        conn.close()

    def export_detailed_report(self, format='csv'):
        """Export all logged data to a file."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM activity_logs", conn)
        conn.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"activity_detailed_{timestamp}"
        
        if format == 'csv':
            df.to_csv(f"{filename}.csv", index=False)
        else:
            df.to_json(f"{filename}.json", orient='records', indent=2)
        
        return filename + '.' + format

    def generate_summary_report(self):
        """Generate various summary statistics from the logged data."""
        conn = sqlite3.connect(self.db_path)
        
        # Application usage summary
        app_summary = pd.read_sql_query("""
            SELECT 
                application,
                COUNT(*) * 5 as total_seconds,
                COUNT(*) as samples,
                AVG(cpu_percent) as avg_cpu,
                AVG(memory_percent) as avg_memory
            FROM activity_logs 
            GROUP BY application 
            ORDER BY total_seconds DESC
        """, conn)
        
        # Time-based patterns
        hour_summary = pd.read_sql_query("""
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as activity_count,
                AVG(cpu_percent) as avg_cpu
            FROM activity_logs 
            GROUP BY hour 
            ORDER BY hour
        """, conn)
        
        conn.close()
        
        return {
            'app_summary': app_summary,
            'hour_summary': hour_summary
        }

    def monitor(self, interval: int = 5):
        """Main monitoring loop with enhanced data collection."""
        print(f"Starting enhanced activity monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop monitoring")
        
        start_time = datetime.now()
        sample_count = 0
        
        try:
            while True:
                window_info = self.get_active_window_info()
                system_info = self.get_system_info()
                self.log_activity(window_info, system_info)
                
                sample_count += 1
                duration = (datetime.now() - start_time).total_seconds()
                
                # Print current status
                print(f"\rRunning for: {int(duration)}s | Samples: {sample_count} | "
                      f"Current: {window_info['application']} | "
                      f"CPU: {system_info['cpu_percent']}% | "
                      f"Memory: {system_info['memory_percent']}%", end='', flush=True)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nStopping monitoring")
            
        finally:
            # Export detailed data
            export_file = self.export_detailed_report('csv')
            print(f"\nDetailed data exported to: {export_file}")
            
            # Generate and display summary
            print("\nGenerating summary report...")
            reports = self.generate_summary_report()
            
            print("\nApplication Summary:")
            print(tabulate(reports['app_summary'], headers='keys', 
                         tablefmt='grid', showindex=False))
            
            print("\nHourly Activity Pattern:")
            print(tabulate(reports['hour_summary'], headers='keys', 
                         tablefmt='grid', showindex=False))

if __name__ == "__main__":
    monitor = EnhancedMacMonitor()
    monitor.monitor()