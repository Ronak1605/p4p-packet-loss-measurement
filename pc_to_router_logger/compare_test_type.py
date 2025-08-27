import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import csv
import glob
from pathlib import Path

def get_csv_files(directory_path):
    """Get all CSV files in a directory."""
    return glob.glob(os.path.join(directory_path, "*.csv"))

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
        
        # Extract metadata
        metadata = {}
        for i in range(data_start_idx - 1):
            if lines[i].strip() and ',' in lines[i]:
                key, value = lines[i].split(',', 1)
                metadata[key.strip()] = value.strip()
        
        # Attach metadata to dataframe as attributes
        df.metadata = metadata
        
        # Try to ensure 'time' column exists (response time is a proxy for time in ms)
        if 'Response Time (ms)' in df.columns and 'time' not in df.columns:
            df['time'] = df['Response Time (ms)'] / 1000  # Convert ms to seconds
        
        # Try to create success column based on Status
        if 'Status' in df.columns and 'success' not in df.columns:
            df['success'] = df['Status'].apply(lambda x: 1 if x == 'Success' else 0)
        
        return df
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def extract_test_metrics(csv_file):
    """Extract key metrics from a test result CSV file."""
    df = read_csv_data(csv_file)
    if df is None:
        return None
    
    # Extract file name without path and extension
    test_name = os.path.basename(csv_file).replace('.csv', '')
    
    # Calculate metrics
    metrics = {
        'test_name': test_name,
    }
    
    # Try to get metrics from metadata if available
    if hasattr(df, 'metadata'):
        if 'Total Duration (s)' in df.metadata:
            metrics['total_time'] = float(df.metadata.get('Total Duration (s)', 0))
        if 'Mean Response Time (ms)' in df.metadata:
            metrics['mean_time'] = float(df.metadata.get('Mean Response Time (ms)', 0)) / 1000  # Convert ms to seconds
        if 'Loss %' in df.metadata:
            metrics['success_rate'] = 100 - float(df.metadata.get('Loss %', 0))  # Convert loss % to success %
        if 'Total Attempts' in df.metadata:
            metrics['num_samples'] = int(df.metadata.get('Total Attempts', 0))
    
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

def compare_test_types(base_path, test_type1, test_type2, config_path=None):
    """Compare metrics between two test types."""
    # Paths for the two test types
    path1 = os.path.join(base_path, test_type1)
    path2 = os.path.join(base_path, test_type2)
    
    # Find all CSV files recursively
    files1 = []
    files2 = []
    
    for root, _, _ in os.walk(path1):
        files1.extend(get_csv_files(root))
    
    for root, _, _ in os.walk(path2):
        files2.extend(get_csv_files(root))
    
    # Extract metrics
    metrics1 = [extract_test_metrics(file) for file in files1]
    metrics1 = [m for m in metrics1 if m is not None]
    
    metrics2 = [extract_test_metrics(file) for file in files2]
    metrics2 = [m for m in metrics2 if m is not None]
    
    # Convert to DataFrames
    df1 = pd.DataFrame(metrics1)
    df2 = pd.DataFrame(metrics2)
    
    # Add test type column
    df1['test_type'] = test_type1
    df2['test_type'] = test_type2
    
    # Combine DataFrames
    combined_df = pd.concat([df1, df2])
    
    return combined_df

def visualize_comparison(combined_df, test_type1, test_type2, output_dir="comparison_plots"):
    """Create visualizations comparing the two test types."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set larger font sizes for all plots - matching compare_cable_types.py style
    plt.rcParams.update({
        'font.size': 20,
        'axes.titlesize': 20,
        'axes.labelsize': 20,
        'xtick.labelsize': 20,
        'ytick.labelsize': 20,
        'legend.fontsize': 20,
        'figure.titlesize': 20,
    })
    
    # Filter data for each test type
    df1 = combined_df[combined_df['test_type'] == test_type1]
    df2 = combined_df[combined_df['test_type'] == test_type2]
    
    # Calculate statistics
    stats = {
        'metric': ['mean_time', 'total_time', 'success_rate'],
        f'{test_type1}_mean': [df1['mean_time'].mean(), df1['total_time'].mean(), df1['success_rate'].mean()],
        f'{test_type1}_std': [df1['mean_time'].std(), df1['total_time'].std(), df1['success_rate'].std()],
        f'{test_type2}_mean': [df2['mean_time'].mean(), df2['total_time'].mean(), df2['success_rate'].mean()],
        f'{test_type2}_std': [df2['mean_time'].std(), df2['total_time'].std(), df2['success_rate'].std()],
    }
    
    stats_df = pd.DataFrame(stats)
    
    # Save statistics to CSV
    stats_df.to_csv(os.path.join(output_dir, 'test_type_comparison_stats.csv'), index=False)
    
    # Define consistent colors for test types
    type1_color = 'blue'
    type2_color = 'red'
    
    # 1. Box plot comparison
    print("Generating box plot comparison...")
    fig, ax = plt.figure(figsize=(14, 9)), plt.gca()
    
    metrics = ['mean_time', 'total_time']
    
    for i, metric in enumerate(metrics):
        plt.subplot(1, 2, i+1)
        
        data = [
            combined_df[combined_df['test_type'] == test_type1][metric],
            combined_df[combined_df['test_type'] == test_type2][metric]
        ]
        
        # Create box plot with custom colors
        boxes = plt.boxplot(data, labels=[test_type1, test_type2], patch_artist=True)
        
        # Set box colors
        boxes['boxes'][0].set(facecolor=type1_color, alpha=0.7, linewidth=2)
        boxes['boxes'][1].set(facecolor=type2_color, alpha=0.7, linewidth=2)
        
        # Make median lines thicker and black
        for median in boxes['medians']:
            median.set(color='black', linewidth=2)
        
        # Make whiskers and caps thicker
        for whisker in boxes['whiskers']:
            whisker.set(linewidth=2)
        for cap in boxes['caps']:
            cap.set(linewidth=2)
            
        # Add value labels for median
        for i, line in enumerate(boxes['medians']):
            x, y = line.get_xydata()[1]
            plt.text(x, y, f'Median: {data[i].median():.3f}', 
                    horizontalalignment='center', verticalalignment='bottom',
                    fontsize=16, fontweight='bold')
        
        # Add value labels for means
        means = [data[0].mean(), data[1].mean()]
        for i, mean_val in enumerate(means):
            plt.text(i+1, mean_val, f'Mean: {mean_val:.3f}', 
                    horizontalalignment='center', verticalalignment='bottom',
                    fontsize=16, fontweight='bold')
        
        plt.title(f'{metric} Comparison', fontsize=20, fontweight='bold')
        plt.ylabel('Time (seconds)', fontsize=20)
        plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'boxplot_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Bar chart for mean values
    # Mean Response Time Bar Chart
    print("Generating mean response time bar chart...")
    fig, ax = plt.subplots(figsize=(10, 7))

    labels = ["Base HTTP", "HTTP With Reconnection"]
    mean_response_times = [df1['mean_time'].mean(), df2['mean_time'].mean()]
    std_response_times = [df1['mean_time'].std(), df2['mean_time'].std()]

    bars = ax.bar(labels, mean_response_times, color=[type1_color, type2_color], alpha=0.7, edgecolor='none')

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.4f}s',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Mean Response Time (seconds)', fontsize=20)
    ax.set_title('Mean Response Time Comparison across 1500 Packet Tests', fontsize=22, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.tick_params(axis='both', labelsize=18)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'mean_response_time_bar_chart.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # Mean Duration Bar Chart
    print("Generating mean duration bar chart...")
    fig, ax = plt.subplots(figsize=(10, 7))

    mean_durations = [df1['total_time'].mean(), df2['total_time'].mean()]
    std_durations = [df1['total_time'].std(), df2['total_time'].std()]

    bars = ax.bar(labels, mean_durations, color=[type1_color, type2_color], alpha=0.7, edgecolor='none')

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}s',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Mean Test Duration (seconds)', fontsize=20)
    ax.set_title('Mean Test Duration Comparison across 1500 Packet Tests', fontsize=22, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.tick_params(axis='both', labelsize=18)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'mean_duration_bar_chart.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Success rate comparison if available
    if 'success_rate' in combined_df.columns and not combined_df['success_rate'].isna().all():
        print("Generating success rate comparison...")
        fig, ax = plt.figure(figsize=(10, 8)), plt.gca()
        
        success_means = [df1['success_rate'].mean(), df2['success_rate'].mean()]
        success_stds = [df1['success_rate'].std(), df2['success_rate'].std()]
        
        bars = plt.bar(["Base HTTP", "HTTP With Reconnection"], success_means, 
                       color=[type1_color, type2_color], alpha=0.7,
                       yerr=success_stds, capsize=5)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=16, fontweight='bold')
        
        plt.ylabel('Success Rate (%)', fontsize=20)
        plt.title('Success Rate Comparison across 1500 Packet Tests', fontsize=24, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.ylim(0, 105)  # Set y-axis to start at 0 and have room for labels
        
        # Make tick labels larger
        plt.setp(ax.get_xticklabels(), fontsize=20)
        plt.setp(ax.get_yticklabels(), fontsize=20)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'success_rate_comparison.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    # 4. Detailed statistical summary table
    print("Generating detailed statistical summary...")
    summary_data = []
    
    # Add statistics for test_type1
    for file in df1['test_name'].unique():
        file_data = combined_df[(combined_df['test_type'] == test_type1) & (combined_df['test_name'] == file)]
        if not file_data.empty:
            summary_data.append({
                'Test Name': file,
                'Test Type': test_type1,
                'Mean Time (s)': round(file_data['mean_time'].iloc[0], 4),
                'Total Time (s)': round(file_data['total_time'].iloc[0], 2),
                'Success Rate (%)': round(file_data['success_rate'].iloc[0], 2),
                'Sample Count': int(file_data['num_samples'].iloc[0])
            })
    
    # Add statistics for test_type2
    for file in df2['test_name'].unique():
        file_data = combined_df[(combined_df['test_type'] == test_type2) & (combined_df['test_name'] == file)]
        if not file_data.empty:
            summary_data.append({
                'Test Name': file,
                'Test Type': test_type2,
                'Mean Time (s)': round(file_data['mean_time'].iloc[0], 4),
                'Total Time (s)': round(file_data['total_time'].iloc[0], 2),
                'Success Rate (%)': round(file_data['success_rate'].iloc[0], 2),
                'Sample Count': int(file_data['num_samples'].iloc[0])
            })
    
    # Create and save the detailed summary
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(os.path.join(output_dir, 'detailed_test_summary.csv'), index=False)
    
    print(f"Visualizations saved to {output_dir}/")
    
    # Print a summary to console
    print("\nTest Type Comparison Summary:")
    print("\nAverage Metrics by Test Type:")
    print(stats_df.to_string(index=False))
    
    print("\nIndividual Test Files Summary:")
    print(summary_df.to_string(index=False))
    
    return stats_df

if __name__ == "__main__":
    # Base path for the results
    base_path = os.path.join(Path(__file__).parent, "results2")
    
    # Test types to compare
    test_type1 = "tcp"
    test_type2 = "tcp&http_reconnect"
    
    # Compare test types
    combined_df = compare_test_types(base_path, test_type1, test_type2)
    
    # Create visualizations
    output_dir = os.path.join(Path(__file__).parent, "comparison_plots")
    visualize_comparison(combined_df, test_type1, test_type2, output_dir)