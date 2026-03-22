#!/usr/bin/env python3
"""
Mission Success Test Script for MedGuide.

Automated test harness that executes a mission sequence and measures:
  - Mission completion rate
  - Time per goal
  - Emergency stop incidents
  - Overall success metrics

This script connects to the running MedGuide system and monitors mission execution,
collecting metrics to a CSV file for analysis.

Usage:
    python3 test_mission.py --output results.csv --loops 3
"""

import argparse
import csv
import time
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped

from medguide_utils.types import MissionStatus, MissionMetrics


class MissionTestMonitor(Node):
    """Monitor mission execution and record metrics."""

    def __init__(self):
        super().__init__('mission_test_monitor')
        
        # Subscriptions
        self.mission_status_sub = self.create_subscription(
            String,
            '/mission_status',
            self._mission_status_callback,
            10
        )
        
        self.emergency_stop_sub = self.create_subscription(
            Bool,
            '/emergency_stop',
            self._emergency_stop_callback,
            10
        )
        
        # Tracking
        self.mission_status = ""
        self.emergency_stops = 0
        self.emergency_stop_active = False
        self.start_time = time.time()
        self.test_complete = False
        
    def _mission_status_callback(self, msg: String):
        """Track mission status updates."""
        self.mission_status = msg.data
        status_lower = msg.data.lower()
        
        if "mission_complete" in status_lower:
            self.test_complete = True
            elapsed = time.time() - self.start_time
            self.get_logger().info(f"Mission completed in {elapsed:.2f} seconds")
            self.get_logger().info(f"Mission status: {msg.data}")
        
        elif "emergency_stop" in status_lower:
            if "triggered" in status_lower:
                self.emergency_stops += 1
                self.get_logger().warn(f"Emergency stop #{self.emergency_stops}")

    def _emergency_stop_callback(self, msg: Bool):
        """Track emergency stop state."""
        if msg.data != self.emergency_stop_active:
            self.emergency_stop_active = msg.data
            if msg.data:
                self.get_logger().warn("Emergency stop activated")
            else:
                self.get_logger().info("Emergency stop cleared")

    def get_elapsed_time(self):
        """Get elapsed test time."""
        return time.time() - self.start_time


def run_mission_test(test_duration: int = 180) -> dict:
    """
    Run a single mission test.
    
    Args:
        test_duration: Maximum test duration in seconds
        
    Returns:
        Dictionary with test metrics
    """
    rclpy.init()
    monitor = MissionTestMonitor()
    
    print(f"\n{'='*60}")
    print("MedGuide Mission Test Starting")
    print(f"Max duration: {test_duration}s")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'status': 'RUNNING',
        'duration_seconds': 0,
        'emergency_stops': 0,
        'final_mission_status': '',
        'success': False,
    }
    
    try:
        while not monitor.test_complete:
            rclpy.spin_once(monitor, timeout_sec=0.1)
            
            elapsed = time.time() - start_time
            
            # Timeout check
            if elapsed > test_duration:
                print(f"\n⏱  TEST TIMEOUT after {elapsed:.1f}s")
                print(f"Current mission status: {monitor.mission_status}")
                test_results['status'] = 'TIMEOUT'
                break
            
            # Print progress
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                sys.stdout.write(f"\r[{elapsed:3.0f}s] Status: {monitor.mission_status[:50]}")
                sys.stdout.flush()
    
    except KeyboardInterrupt:
        print("\n\nTEST INTERRUPTED by user")
        test_results['status'] = 'INTERRUPTED'
    
    except Exception as e:
        print(f"\nTEST ERROR: {e}")
        test_results['status'] = 'ERROR'
    
    finally:
        # Collect final results
        elapsed = time.time() - start_time
        test_results['duration_seconds'] = elapsed
        test_results['emergency_stops'] = monitor.emergency_stops
        test_results['final_mission_status'] = monitor.mission_status
        test_results['success'] = 'mission_complete' in monitor.mission_status.lower()
        
        # Print summary
        print(f"\n\n{'='*60}")
        print("Mission Test Complete")
        print(f"{'='*60}")
        print(f"Duration: {elapsed:.2f}s")
        print(f"Status: {test_results['status']}")
        print(f"Success: {'✓ YES' if test_results['success'] else '✗ NO'}")
        print(f"Emergency stops: {test_results['emergency_stops']}")
        print(f"Final mission status: {test_results['final_mission_status']}")
        print(f"{'='*60}\n")
        
        monitor.destroy_node()
        rclpy.shutdown()
    
    return test_results


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description='MedGuide mission success test harness'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='medguide_mission_test_results.csv',
        help='Output CSV file for results'
    )
    parser.add_argument(
        '--loops', '-n',
        type=int,
        default=1,
        help='Number of test loops to run'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=180,
        help='Timeout per test in seconds'
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Collect results
    all_results = []
    
    for loop in range(args.loops):
        print(f"\n\n{'#'*60}")
        print(f"TEST LOOP {loop+1}/{args.loops}")
        print(f"{'#'*60}")
        
        result = run_mission_test(test_duration=args.timeout)
        result['loop'] = loop + 1
        all_results.append(result)
        
        # Delay between loops
        if loop < args.loops - 1:
            print("Waiting 5 seconds before next test loop...")
            time.sleep(5)
    
    # Write results to CSV
    if all_results:
        csv_columns = ['loop', 'timestamp', 'duration_seconds', 'status', 'success', 
                       'emergency_stops', 'final_mission_status']
        
        try:
            with open(args.output, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                
                for result in all_results:
                    row = {k: result.get(k, '') for k in csv_columns}
                    writer.writerow(row)
            
            print(f"\n✓ Results written to: {args.output}")
            
            # Print summary statistics
            success_count = sum(1 for r in all_results if r['success'])
            success_rate = (success_count / len(all_results)) * 100
            avg_duration = sum(r['duration_seconds'] for r in all_results) / len(all_results)
            total_emergency_stops = sum(r['emergency_stops'] for r in all_results)
            
            print(f"\n{'='*60}")
            print("SUMMARY STATISTICS")
            print(f"{'='*60}")
            print(f"Total tests: {len(all_results)}")
            print(f"Successful: {success_count}")
            print(f"Success rate: {success_rate:.1f}%")
            print(f"Average duration: {avg_duration:.2f}s")
            print(f"Total emergency stops: {total_emergency_stops}")
            print(f"{'='*60}\n")
        
        except Exception as e:
            print(f"ERROR writing results: {e}")
            sys.exit(1)
    else:
        print("ERROR: No test results collected")
        sys.exit(1)


if __name__ == '__main__':
    main()
