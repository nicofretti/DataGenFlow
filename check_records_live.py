#!/usr/bin/env python3
import sqlite3
import time
import sys

db_path = "data/qa_records.db"

print("Monitoring database for new records...")
print("Start a job now and watch for records appearing...\n")

last_count = 0
while True:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get count of records
        cursor.execute("SELECT COUNT(*) FROM records")
        count_result = cursor.fetchone()
        current_count = count_result[0] if count_result else 0

        # Get latest record info if count changed
        if current_count != last_count:
            cursor.execute("""
                SELECT id, job_id, created_at
                FROM records
                ORDER BY id DESC
                LIMIT 1
            """)
            latest = cursor.fetchone()
            if latest:
                print(f"[{time.strftime('%H:%M:%S')}] Total records: {current_count} | Latest: ID={latest[0]}, Job={latest[1]}, Time={latest[2]}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Total records: {current_count}")
            last_count = current_count
        elif current_count == 0 and last_count == 0:
            # Print waiting message once
            if 'printed_waiting' not in locals():
                print(f"[{time.strftime('%H:%M:%S')}] Waiting for records... (database is empty)")
                printed_waiting = True

        conn.close()
        time.sleep(1)  # Check every second

    except KeyboardInterrupt:
        print("\nStopped monitoring")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
