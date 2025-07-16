import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import glob
from typing import List, Dict, Any
from pathlib import Path

class TestDataVisualiser:
    def __init__(self, results_folder: str = "results_2"):
        self.results_folder = results_folder
        plt.style.use('seaborn-v0_8')
        
    def load_csv_data(self, csv_path: str) -> Dict[str, Any]:
        """Load and parse CSV data from test results"""
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        
        # Extract metadata
        metadata = {}
        data_start_idx = 0
        
        for i, line in enumerate(lines):
            if line.strip() == "":
                continue
            if "Attempt,Timestamp" in line:
                data_start_idx = i
                break
            if "," in line:
                key, value = line.strip().split(",", 1)
                metadata[key] = value
        
        # Load the actual test data
        df = pd.read_csv(csv_path, skiprows=data_start_idx)
        
        return {
            "metadata": metadata,
            "data": df,
            "file_path": csv_path
        }
    
    def plot_response_times(self, test_data: Dict[str, Any], save_path: str = None):
        """Plot response times over test attempts"""
        df = test_data["data"]
        metadata = test_data["metadata"]
        
        # Filter successful responses
        success_df = df[df['Status'] == 'Success'].copy()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Time series plot
        ax1.plot(success_df['Attempt'], success_df['Response Time (ms)'], 'b-o', markersize=3)
        ax1.set_xlabel('Test Attempt')
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title(f'Response Times - {metadata.get("Cable Type", "Unknown")} Connection')
        ax1.grid(True, alpha=0.3)
        
        # Add statistics annotations
        mean_time = success_df['Response Time (ms)'].mean()
        ax1.axhline(y=mean_time, color='r', linestyle='--', alpha=0.7, label=f'Mean: {mean_time:.2f} ms')
        ax1.legend()
        
        # Histogram
        ax2.hist(success_df['Response Time (ms)'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.set_xlabel('Response Time (ms)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Response Time Distribution')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_measurement_values(self, test_data: Dict[str, Any], save_path: str = None):
        """Plot voltage and current measurements"""
        df = test_data["data"]
        metadata = test_data["metadata"]
        
        # Filter successful responses and convert to numeric
        success_df = df[df['Status'] == 'Success'].copy()
        success_df['V RMS CH1 (V)'] = pd.to_numeric(success_df['V RMS CH1 (V)'], errors='coerce')
        success_df['AC RMS CH2 (A)'] = pd.to_numeric(success_df['AC RMS CH2 (A)'], errors='coerce')
        success_df['AC RMS CH3 (A)'] = pd.to_numeric(success_df['AC RMS CH3 (A)'], errors='coerce')
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Voltage plot
        axes[0,0].plot(success_df['Attempt'], success_df['V RMS CH1 (V)'], 'g-o', markersize=3)
        axes[0,0].set_title('Channel 1 Voltage RMS')
        axes[0,0].set_ylabel('Voltage (V)')
        axes[0,0].grid(True, alpha=0.3)
        
        # Current CH2 plot
        axes[0,1].plot(success_df['Attempt'], success_df['AC RMS CH2 (A)'], 'r-o', markersize=3)
        axes[0,1].set_title('Channel 2 Current AC RMS')
        axes[0,1].set_ylabel('Current (A)')
        axes[0,1].grid(True, alpha=0.3)
        
        # Current CH3 plot
        axes[1,0].plot(success_df['Attempt'], success_df['AC RMS CH3 (A)'], 'b-o', markersize=3)
        axes[1,0].set_title('Channel 3 Current AC RMS')
        axes[1,0].set_xlabel('Test Attempt')
        axes[1,0].set_ylabel('Current (A)')
        axes[1,0].grid(True, alpha=0.3)
        
        # Combined current comparison
        axes[1,1].plot(success_df['Attempt'], success_df['AC RMS CH2 (A)'], 'r-o', markersize=3, label='CH2')
        axes[1,1].plot(success_df['Attempt'], success_df['AC RMS CH3 (A)'], 'b-o', markersize=3, label='CH3')
        axes[1,1].set_title('Current Comparison CH2 vs CH3')
        axes[1,1].set_xlabel('Test Attempt')
        axes[1,1].set_ylabel('Current (A)')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        plt.suptitle(f'Measurement Values - {metadata.get("Cable Type", "Unknown")} Connection')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def compare_multiple_tests(self, csv_paths: List[str], save_path: str = None):
        """Compare response times across multiple test files"""
        test_data_list = []
        
        for path in csv_paths:
            data = self.load_csv_data(path)
            test_data_list.append(data)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Response time comparison
        for i, test_data in enumerate(test_data_list):
            df = test_data["data"]
            metadata = test_data["metadata"]
            success_df = df[df['Status'] == 'Success']
            
            label = f"{metadata.get('Cable Type', 'Unknown')} - {Path(test_data['file_path']).stem}"
            ax1.plot(success_df['Attempt'], success_df['Response Time (ms)'], 
                    'o-', markersize=2, label=label, alpha=0.7)
        
        ax1.set_xlabel('Test Attempt')
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title('Response Time Comparison')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot comparison
        response_times_data = []
        labels = []
        
        for test_data in test_data_list:
            df = test_data["data"]
            metadata = test_data["metadata"]
            success_df = df[df['Status'] == 'Success']
            response_times_data.append(success_df['Response Time (ms)'].values)
            labels.append(f"{metadata.get('Cable Type', 'Unknown')}")
        
        ax2.boxplot(response_times_data, labels=labels)
        ax2.set_ylabel('Response Time (ms)')
        ax2.set_title('Response Time Distribution Comparison')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def create_summary_report(self, csv_paths: List[str], save_path: str = None):
        """Create a comprehensive summary report"""
        summary_data = []
        
        for path in csv_paths:
            data = self.load_csv_data(path)
            metadata = data["metadata"]
            df = data["data"]
            success_df = df[df['Status'] == 'Success']
            
            summary = {
                'Test File': Path(path).name,
                'Cable Type': metadata.get('Cable Type', 'Unknown'),
                'Position': metadata.get('Position', 'Unknown'),
                'Power State': metadata.get('Power State', 'Unknown'),
                'Total Attempts': int(metadata.get('Total Attempts', 0)),
                'Successful': int(metadata.get('Successful Responses', 0)),
                'Lost Packets': int(metadata.get('Lost Packets', 0)),
                'Loss %': float(metadata.get('Loss %', 0)),
                'Mean Time (ms)': success_df['Response Time (ms)'].mean() if not success_df.empty else 0,
                'Median Time (ms)': success_df['Response Time (ms)'].median() if not success_df.empty else 0,
                'Min Time (ms)': success_df['Response Time (ms)'].min() if not success_df.empty else 0,
                'Max Time (ms)': success_df['Response Time (ms)'].max() if not success_df.empty else 0,
                'Std Dev (ms)': success_df['Response Time (ms)'].std() if not success_df.empty else 0
            }
            summary_data.append(summary)
        
        summary_df = pd.DataFrame(summary_data)
        
        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Loss percentage comparison
        axes[0,0].bar(range(len(summary_df)), summary_df['Loss %'], 
                     color=['red' if x > 0 else 'green' for x in summary_df['Loss %']])
        axes[0,0].set_title('Packet Loss Percentage by Test')
        axes[0,0].set_ylabel('Loss %')
        axes[0,0].set_xticks(range(len(summary_df)))
        axes[0,0].set_xticklabels([f"{row['Cable Type']}\n{i+1}" for i, (_, row) in enumerate(summary_df.iterrows())], 
                                 rotation=45)
        
        # Mean response time comparison
        axes[0,1].bar(range(len(summary_df)), summary_df['Mean Time (ms)'])
        axes[0,1].set_title('Mean Response Time by Test')
        axes[0,1].set_ylabel('Mean Time (ms)')
        axes[0,1].set_xticks(range(len(summary_df)))
        axes[0,1].set_xticklabels([f"{row['Cable Type']}\n{i+1}" for i, (_, row) in enumerate(summary_df.iterrows())], 
                                 rotation=45)
        
        # Response time statistics
        x_pos = np.arange(len(summary_df))
        width = 0.25
        
        axes[1,0].bar(x_pos - width, summary_df['Min Time (ms)'], width, label='Min', alpha=0.7)
        axes[1,0].bar(x_pos, summary_df['Mean Time (ms)'], width, label='Mean', alpha=0.7)
        axes[1,0].bar(x_pos + width, summary_df['Max Time (ms)'], width, label='Max', alpha=0.7)
        axes[1,0].set_title('Response Time Statistics')
        axes[1,0].set_ylabel('Time (ms)')
        axes[1,0].set_xticks(x_pos)
        axes[1,0].set_xticklabels([f"{row['Cable Type']}\n{i+1}" for i, (_, row) in enumerate(summary_df.iterrows())], 
                                 rotation=45)
        axes[1,0].legend()
        
        # Success rate
        axes[1,1].bar(range(len(summary_df)), 
                     (summary_df['Successful'] / summary_df['Total Attempts']) * 100,
                     color=['red' if x < 100 else 'green' for x in (summary_df['Successful'] / summary_df['Total Attempts']) * 100])
        axes[1,1].set_title('Success Rate by Test')
        axes[1,1].set_ylabel('Success Rate %')
        axes[1,1].set_xticks(range(len(summary_df)))
        axes[1,1].set_xticklabels([f"{row['Cable Type']}\n{i+1}" for i, (_, row) in enumerate(summary_df.iterrows())], 
                                 rotation=45)
        axes[1,1].set_ylim([0, 105])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return summary_df
    
    def find_csv_files(self, pattern: str = "*.csv") -> List[str]:
        """Find all CSV files matching pattern in results folder"""
        search_path = os.path.join(self.results_folder, "**", pattern)
        return glob.glob(search_path, recursive=True)

# Example usage functions
def visualise_single_test(csv_path: str):
    """Visualise a single test file"""
    visualiser = TestDataVisualiser()
    test_data = visualiser.load_csv_data(csv_path)
    
    print(f"Test Metadata:")
    for key, value in test_data["metadata"].items():
        print(f"  {key}: {value}")
    
    visualiser.plot_response_times(test_data)
    visualiser.plot_measurement_values(test_data)

def compare_usb_vs_lan():
    """Compare USB vs LAN test results"""
    visualiser = TestDataVisualiser()
    
    # Find USB and LAN test files
    usb_files = glob.glob("results_2/**/usb_test_results*.csv", recursive=True)
    lan_files = glob.glob("results_2/**/lan_test_results*.csv", recursive=True)
    
    if usb_files and lan_files:
        # Take the most recent of each type
        csv_paths = [usb_files[-1], lan_files[-1]]
        visualiser.compare_multiple_tests(csv_paths)
    else:
        print("Could not find both USB and LAN test files")

def create_comprehensive_report():
    """Create a comprehensive report of all test results"""
    visualiser = TestDataVisualiser()
    csv_files = visualiser.find_csv_files()
    
    if csv_files:
        print(f"Found {len(csv_files)} test files")
        summary_df = visualiser.create_summary_report(csv_files)
        print("\nSummary Statistics:")
        print(summary_df.to_string(index=False))
        
        # Save summary to CSV
        summary_df.to_csv("test_summary_report.csv", index=False)
        print("\nSummary report saved to 'test_summary_report.csv'")
    else:
        print("No CSV files found in results folder")

if __name__ == "__main__":
    # Example: Visualise the provided test file
    test_file = "results_2/usb/test_switches/no_power/mc_off/usb_test_results_usb_test_switches_no_power_mc_off_test_0001.csv"
    
    print("Visualizing single test file...")
    visualise_single_test(test_file)
    
    print("\nCreating comprehensive report...")
    create_comprehensive_report()