import time
import datetime
import sqlite3
from typing import Dict
import subprocess
import pandas as pd
import json
from tabulate import tabulate

class MacProductivityMonitor:
    def __init__(self, db_path: str = "productivity.db"):
        """Initialize the productivity monitor with database connection."""
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Create the SQLite database and tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Drop existing table if it exists
        c.execute('DROP TABLE IF EXISTS activity_logs')
        
        # Create new table with updated schema
        c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            timestamp TEXT,
            window_title TEXT,
            application TEXT,
            duration INTEGER
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
                    'application': app_name.strip()  # Removed .lower() to preserve original case
                }
            
        except Exception as e:
            print(f"Error getting window info: {e}")
            
        return {
            'window_title': 'unknown',
            'application': 'unknown'
        }

    def log_activity(self, window_info: Dict[str, str], duration: int):
        """Log the activity to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
        INSERT INTO activity_logs
        VALUES (?, ?, ?, ?)
        ''', (
            datetime.datetime.now().isoformat(),
            window_info['window_title'],
            window_info['application'],
            duration
        ))
        
        conn.commit()
        conn.close()

    def generate_report(self, days: int = 1) -> pd.DataFrame:
        """Generate an activity report for the specified number of days."""
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT 
            application,
            SUM(duration) as total_duration,
            COUNT(*) as number_of_switches,
            AVG(duration) as avg_duration
        FROM activity_logs
        WHERE timestamp >= datetime('now', '-{days} days')
        GROUP BY application
        ORDER BY total_duration DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert durations to more readable format
        df['total_duration'] = df['total_duration'].apply(lambda x: f"{x//60}m {x%60}s")
        df['avg_duration'] = df['avg_duration'].apply(lambda x: f"{int(x//60)}m {int(x%60)}s")
        
        return df

    def monitor(self, interval: int = 5):
        """Main monitoring loop. Tracks activity at specified interval."""
        print(f"Starting activity monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                window_info = self.get_active_window_info()
                self.log_activity(window_info, interval)
                
                # Print current activity
                print(f"\rCurrent: {window_info['application']} - {window_info['window_title']}", end='', flush=True)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nStopping activity monitoring")
            
        finally:
            # Generate and display report
            print("\nActivity Report:")
            report = self.generate_report()
            print("\n" + tabulate(report, headers='keys', tablefmt='grid', showindex=False))

if __name__ == "__main__":
    monitor = MacProductivityMonitor()
    monitor.monitor()