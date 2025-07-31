#!/usr/bin/env python3
import sys
import argparse
import os
import importlib.util

# Ensure we can import the data_visualiser module
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import with fallback approach
try:
    from data_visualiser import TestDataVisualiser, visualise_single_test, compare_usb_vs_lan, create_comprehensive_report
except ImportError:
    # Alternative import approach
    spec = importlib.util.spec_from_file_location("data_visualiser", 
                                                 os.path.join(current_dir, "data_visualiser.py"))
    data_visualiser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_visualiser)
    
    TestDataVisualiser = data_visualiser.TestDataVisualiser
    visualise_single_test = data_visualiser.visualise_single_test
    compare_usb_vs_lan = data_visualiser.compare_usb_vs_lan
    create_comprehensive_report = data_visualiser.create_comprehensive_report
    
def main():
    parser = argparse.ArgumentParser(description='Visualise packet loss test data')
    parser.add_argument('--single', type=str, help='Path to single CSV file to visualise')
    parser.add_argument('--compare', nargs='+', help='Paths to multiple CSV files to compare')
    parser.add_argument('--report', action='store_true', help='Create comprehensive report of all tests')
    parser.add_argument('--usb-vs-lan', action='store_true', help='Compare latest USB vs LAN tests')
    parser.add_argument('--latest', action='store_true', help='Visualise the most recent test file')
    
    args = parser.parse_args()
    
    if args.single:
        if os.path.exists(args.single):
            print(f"Visualizing: {args.single}")
            visualise_single_test(args.single)
        else:
            print(f"Error: File '{args.single}' not found!")
            sys.exit(1)
    
    elif args.compare:
        missing_files = [f for f in args.compare if not os.path.exists(f)]
        if missing_files:
            print(f"Error: Files not found: {missing_files}")
            sys.exit(1)
        
        print(f"Comparing {len(args.compare)} test files")
        visualiser = TestDataVisualiser()
        visualiser.compare_multiple_tests(args.compare)
    
    elif args.report:
        print("Creating comprehensive report...")
        create_comprehensive_report()
    
    elif args.usb_vs_lan:
        print("Comparing USB vs LAN tests...")
        compare_usb_vs_lan()
    
    elif args.latest:
        print("Finding most recent test file...")
        visualiser = TestDataVisualiser()
        csv_files = visualiser.find_csv_files()
        if csv_files:
            # Sort by modification time to get the most recent
            latest_file = max(csv_files, key=os.path.getmtime)
            print(f"Visualizing latest test: {latest_file}")
            visualise_single_test(latest_file)
        else:
            print("No CSV test files found!")
            sys.exit(1)
    
    else:
        # Show help if no arguments provided
        parser.print_help()
        
        # Optionally show available files
        print("\nAvailable test files:")
        visualiser = TestDataVisualiser()
        csv_files = visualiser.find_csv_files()
        if csv_files:
            for i, file in enumerate(csv_files[-5:], 1):  # Show last 5 files
                print(f"  {i}. {file}")
            if len(csv_files) > 5:
                print(f"  ... and {len(csv_files) - 5} more files")
        else:
            print("  No CSV files found in results_2 folder")

if __name__ == "__main__":
    main()