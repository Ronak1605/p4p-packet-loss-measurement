import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import csv
import glob
from pathlib import Path
import re

def get_csv_files(directory_path, exclude_pattern=None):
    """Get all CSV files in a directory."""
    csv_files = glob.glob(os.path.join(directory_path, "*.csv"))
    
    if exclude_pattern:
        csv_files = [f for f in csv_files if not re.search(exclude_pattern, f)]
    
    return csv_files

def read_csv_data(file_path):
    """Read data from a CSV file."""
    try:
        # First, determine the structure of the file
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        # Find the blank line that separates metadata from data
        data_start_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "":
                data_start_idx = i + 1
                break
        
        # If no blank line found, try to find the line with column headers
        if data_start_idx is None:
            for i, line in enumerate(lines):
                if "Attempt" in line:
                    data_start_idx = i
                    break
        
        if data_start_idx is None:
            print(f"Could not determine data structure in {file_path}")
            return None
        
        # Read the data section only
        df = pd.read_csv(file_path, skiprows=data_start_idx)
        
        # Extract metadata to a separate dictionary
        metadata = {}
        for i in range(min(data_start_idx - 1, len(lines))):
            if lines[i].strip() and ',' in lines[i]:
                key, value = lines[i].split(',', 1)
                metadata[key.strip()] = value.strip()
        
        # Store metadata in a special column instead of as an attribute
        # This avoids the warning
        df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
        df['_metadata_dict'] = str(metadata)  # Store as string in a column
        
        # Try to ensure 'time' column exists (response time is a proxy for time in ms)
        if 'Response Time (ms)' in df.columns and 'time' not in df.columns:
            df['time'] = df['Response Time (ms)'] / 1000  # Convert ms to seconds
        
        # Try to create success column based on Status
        if 'Status' in df.columns and 'success' not in df.columns:
            df['success'] = df['Status'].apply(lambda x: 1 if x == 'Success' else 0)
        
        return df, metadata  # Return both the dataframe and metadata separately
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, None

def extract_test_metrics(csv_file):
    """Extract key metrics from a test result CSV file."""
    result = read_csv_data(csv_file)
    if result[0] is None:
        return None
    
    df, metadata = result
    
    # Extract file name without path and extension
    test_name = os.path.basename(csv_file).replace('.csv', '')
    
    # Calculate metrics
    metrics = {
        'test_name': test_name,
    }
    
    # Try to get metrics from metadata if available
    if metadata:
        if 'Total Duration (s)' in metadata:
            metrics['total_time'] = float(metadata.get('Total Duration (s)', 0))
        if 'Mean Response Time (ms)' in metadata:
            metrics['mean_time'] = float(metadata.get('Mean Response Time (ms)', 0)) / 1000  # Convert ms to seconds
        if 'Loss %' in metadata:
            metrics['success_rate'] = 100 - float(metadata.get('Loss %', 0))  # Convert loss % to success %
        if 'Total Attempts' in metadata:
            metrics['num_samples'] = int(metadata.get('Total Attempts', 0))
    
    # Fall back to calculating from data if metadata isn't available
    if 'total_time' not in metrics and 'time' in df.columns:
        metrics['total_time'] = df['time'].max() - df['time'].min()
    if 'mean_time' not in metrics and 'time' in df.columns:
        metrics['mean_time'] = df['time'].diff().mean()
    if 'success_rate' not in metrics and 'success' in df.columns:
        metrics['success_rate'] = (df['success'].sum() / len(df)) * 100
    if 'num_samples' not in metrics:
        metrics['num_samples'] = len(df)
    
    return metrics

def compare_cable_modifications(base_path, modified_path, unmodified_path, output_dir="cable_modification_comparison"):
    """Compare modified vs unmodified cable performance."""
    # Get CSV files for both cable types, excluding tests with 1000 attempts
    modified_files = get_csv_files(modified_path, exclude_pattern="1000_attempt")
    unmodified_files = get_csv_files(unmodified_path)
    
    # Extract metrics
    modified_metrics = [extract_test_metrics(file) for file in modified_files]
    modified_metrics = [m for m in modified_metrics if m is not None]
    
    unmodified_metrics = [extract_test_metrics(file) for file in unmodified_files]
    unmodified_metrics = [m for m in unmodified_metrics if m is not None]
    
    # Convert to DataFrames
    modified_df = pd.DataFrame(modified_metrics)
    unmodified_df = pd.DataFrame(unmodified_metrics)
    
    # Add cable type column
    modified_df['cable_type'] = 'Modified'
    unmodified_df['cable_type'] = 'Unmodified'
    
    # Combine DataFrames
    combined_df = pd.concat([modified_df, unmodified_df])
    
    # Create visualizations - pass file lists for additional visualizations
    visualize_cable_comparison(combined_df, modified_files, unmodified_files, output_dir)
    
    return combined_df

def visualize_cable_comparison(combined_df, modified_files, unmodified_files, output_dir="cable_modification_comparison"):
    """Create visualizations comparing modified vs unmodified cables."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Use seaborn style as in data_visualiser.py
    plt.style.use('seaborn-v0_8')
    
    # Filter data for each cable type
    modified_df = combined_df[combined_df['cable_type'] == 'Modified']
    unmodified_df = combined_df[combined_df['cable_type'] == 'Unmodified']
    
    # Calculate statistics
    stats = {
        'metric': ['mean_time', 'total_time', 'success_rate'],
        'Modified_mean': [modified_df['mean_time'].mean(), modified_df['total_time'].mean(), modified_df['success_rate'].mean()],
        'Modified_std': [modified_df['mean_time'].std(), modified_df['total_time'].std(), modified_df['success_rate'].std()],
        'Unmodified_mean': [unmodified_df['mean_time'].mean(), unmodified_df['total_time'].mean(), unmodified_df['success_rate'].mean()],
        'Unmodified_std': [unmodified_df['mean_time'].std(), unmodified_df['total_time'].std(), unmodified_df['success_rate'].std()],
    }
    
    stats_df = pd.DataFrame(stats)
    
    # Save statistics to CSV
    stats_df.to_csv(os.path.join(output_dir, 'cable_modification_comparison_stats.csv'), index=False)
    
    # Define consistent colors for cable types (use more subtle colors as in data_visualiser)
    modified_color = 'royalblue'
    unmodified_color = 'tomato'
    
    # Get sample size for title
    sample_size = modified_df['num_samples'].mean()
    
    # 1. Box plot comparison
    print("Generating box plot comparison...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    metrics = ['mean_time', 'total_time']
    metric_labels = ['Mean Response Time', 'Total Test Duration']
    
    for i, (metric, metric_label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[i]
        
        data = [
            combined_df[combined_df['cable_type'] == 'Modified'][metric],
            combined_df[combined_df['cable_type'] == 'Unmodified'][metric]
        ]
        
        # Create box plot with custom colors
        boxes = ax.boxplot(data, labels=['Modified Cable', 'Unmodified Cable'], patch_artist=True)
        
        # Set box colors
        boxes['boxes'][0].set(facecolor=modified_color, alpha=0.7)
        boxes['boxes'][1].set(facecolor=unmodified_color, alpha=0.7)
        
        # Add value labels for median in a better position
        for j, line in enumerate(boxes['medians']):
            x, y = line.get_xydata()[1]
            median_val = data[j].median()
            mean_val = data[j].mean()
            
            # Position text above the median line
            y_offset = 0.05 * (max(data[j].max(), 0.01))
            ax.text(j+1, median_val + y_offset, f'Median: {median_val:.3f}s', 
                    horizontalalignment='center', fontsize=9)
            
            # Add mean value at a different position
            ax.text(j+1, mean_val - y_offset, f'Mean: {mean_val:.3f}s', 
                    horizontalalignment='center', fontsize=9)
        
        ax.set_title(f'{metric_label} Comparison')
        ax.set_ylabel('Time (seconds)')
        ax.grid(True, alpha=0.3)
    
    fig.suptitle(f'LAN Cable Modification Performance Comparison ({int(sample_size)} packets)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'boxplot_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Bar chart for mean response time values
    print("Generating mean comparison bar chart...")
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Just show mean response time
    cable_types = ['Modified Cable', 'Unmodified Cable']
    means = [modified_df['mean_time'].mean(), unmodified_df['mean_time'].mean()]
    stds = [modified_df['mean_time'].std(), unmodified_df['mean_time'].std()]
    
    # Create single-metric bar chart
    bars = ax.bar(cable_types, means, color=[modified_color, unmodified_color], 
                 alpha=0.7, yerr=stds, capsize=5)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.4f}s',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),  # 3 points vertical offset
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylabel('Time (seconds)')
    ax.set_title(f'Mean Response Time Comparison across 500 Packet Tests)')
    ax.grid(True, alpha=0.3)
    
    # Remove spines to eliminate any strange lines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'mean_comparison_bar_chart.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Success rate comparison
    print("Generating success rate comparison...")
    fig, ax = plt.subplots(figsize=(8, 6))
    
    success_means = [modified_df['success_rate'].mean(), unmodified_df['success_rate'].mean()]
    success_stds = [modified_df['success_rate'].std(), unmodified_df['success_rate'].std()]
    
    bars = ax.bar(['Modified Cable', 'Unmodified Cable'], success_means, 
                   color=[modified_color, unmodified_color], alpha=0.7,
                   yerr=success_stds, capsize=5)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 5),  # 5 points vertical offset
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=10)
    
    ax.set_ylabel('Success Rate (%)')
    ax.set_title(f'Packet Success Rate Comparison across 500 Packet Tests')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)  # Set y-axis to start at 0 and have room for labels
    
    # Remove top and right spines to eliminate extra lines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'success_rate_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Response time distribution
    print("Generating response time distributions...")
    fig, ax = plt.subplots(figsize=(10, 6))

    # Combine all response times for each cable type
    modified_responses = []
    unmodified_responses = []

    for file in modified_files:
        result = read_csv_data(file)
        if result[0] is not None:  # Check if df is not None
            df, _ = result  # Unpack the tuple
            if 'Response Time (ms)' in df.columns:
                # Filter only successful responses
                if 'Status' in df.columns:
                    success_df = df[df['Status'] == 'Success']
                    modified_responses.extend(success_df['Response Time (ms)'].tolist())
                else:
                    modified_responses.extend(df['Response Time (ms)'].tolist())

    for file in unmodified_files:
        result = read_csv_data(file)
        if result[0] is not None:  # Check if df is not None
            df, _ = result  # Unpack the tuple
            if 'Response Time (ms)' in df.columns:
                # Filter only successful responses
                if 'Status' in df.columns:
                    success_df = df[df['Status'] == 'Success']
                    unmodified_responses.extend(success_df['Response Time (ms)'].tolist())
                else:
                    unmodified_responses.extend(df['Response Time (ms)'].tolist())
    
    # Calculate bin edges that cover both datasets
    max_response = max(max(modified_responses or [0]), max(unmodified_responses or [0]))
    bins = np.linspace(0, min(max_response, 500), 50)  # Cap at 500ms for better visibility
    
    # Create histograms with alpha for transparency
    ax.hist(modified_responses, bins=bins, alpha=0.6, color=modified_color, label='Modified Cable')
    ax.hist(unmodified_responses, bins=bins, alpha=0.6, color=unmodified_color, label='Unmodified Cable')
    
    ax.set_xlabel('Response Time (ms)')
    ax.set_ylabel('Frequency')
    ax.set_title('Response Time Distribution Comparison')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add annotation with mean values
    mod_mean = np.mean(modified_responses)
    unmod_mean = np.mean(unmodified_responses)
    ax.annotate(f'Modified Mean: {mod_mean:.2f}ms\nUnmodified Mean: {unmod_mean:.2f}ms',
               xy=(0.95, 0.95), xycoords='axes fraction',
               ha='right', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'response_time_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 5. Time series comparison (similar to compare_multiple_tests in data_visualiser.py)
    print("Generating time series comparison...")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Find first file of each type to plot time series
    if modified_files and unmodified_files:
        mod_file = modified_files[0]
        unmod_file = unmodified_files[0]
        
        mod_result = read_csv_data(mod_file)
        unmod_result = read_csv_data(unmod_file)
        
        if mod_result[0] is not None and unmod_result[0] is not None:
            mod_df, _ = mod_result  # Unpack the tuple
            unmod_df, _ = unmod_result  # Unpack the tuple
            
            # Filter successful responses
            mod_success = mod_df[mod_df['Status'] == 'Success'] if 'Status' in mod_df.columns else mod_df
            unmod_success = unmod_df[unmod_df['Status'] == 'Success'] if 'Status' in unmod_df.columns else unmod_df
            
            # Plot time series
            ax.plot(mod_success['Attempt'], mod_success['Response Time (ms)'], 
                'o-', markersize=3, alpha=0.7, color=modified_color, label='Modified Cable')
            ax.plot(unmod_success['Attempt'], unmod_success['Response Time (ms)'], 
                'o-', markersize=3, alpha=0.7, color=unmodified_color, label='Unmodified Cable')
            
            ax.set_xlabel('Test Attempt')
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('Response Time Comparison Over Test Sequence')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'response_time_sequence.png'), dpi=300, bbox_inches='tight')
            plt.close()
    
    # 6. Detailed statistical summary table
    print("Generating detailed statistical summary...")
    summary_data = []
    
    # Add statistics for modified cable
    for file in modified_files:
        file_metrics = extract_test_metrics(file)
        if file_metrics:
            summary_data.append({
                'Test Name': os.path.basename(file).split('_test_')[0],
                'Cable Type': 'Modified Cable',
                'Mean Time (s)': round(file_metrics['mean_time'], 4),
                'Total Time (s)': round(file_metrics['total_time'], 2),
                'Success Rate (%)': round(file_metrics['success_rate'], 2),
                'Sample Count': int(file_metrics['num_samples'])
            })
    
    # Add statistics for unmodified cable
    for file in unmodified_files:
        file_metrics = extract_test_metrics(file)
        if file_metrics:
            summary_data.append({
                'Test Name': os.path.basename(file).split('_test_')[0],
                'Cable Type': 'Unmodified Cable',
                'Mean Time (s)': round(file_metrics['mean_time'], 4),
                'Total Time (s)': round(file_metrics['total_time'], 2),
                'Success Rate (%)': round(file_metrics['success_rate'], 2),
                'Sample Count': int(file_metrics['num_samples'])
            })
    
    # Create and save the detailed summary
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(os.path.join(output_dir, 'detailed_cable_test_summary.csv'), index=False)
    
    print(f"Visualizations saved to {output_dir}/")
    
    # Print a summary to console
    print("\nCable Modification Comparison Summary:")
    print("\nAverage Metrics by Cable Type:")
    print(stats_df.to_string(index=False))
    
    return stats_df

if __name__ == "__main__":
    # Base path
    base_path = os.path.join(Path(__file__).parent)
    
    # Paths for modified and unmodified cable tests
    modified_path = os.path.join(base_path, "results2", "tcp", "lan_cat6_utp", "metal_benchtop_taped", "60V", "120_deg")
    unmodified_path = os.path.join(base_path, "results3", "http", "lan_cat6_utp_normal", "metal_benchtop_taped", "60V", "120_deg")
    
    # Compare cables
    compare_cable_modifications(base_path, modified_path, unmodified_path)