#!/usr/bin/env python3
import os
import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

# Add current directory to path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Handle module import with fallback
try:
    from data_visualiser import TestDataVisualiser
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("data_visualiser", 
                                                 os.path.join(current_dir, "data_visualiser.py"))
    data_visualiser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_visualiser)
    TestDataVisualiser = data_visualiser.TestDataVisualiser

def compare_cable_types(shielded_files, unshielded_files, save_dir="comparison_plots"):
    """
    Compare shielded vs unshielded cable tests with consistent color coding
    
    Args:
        shielded_files: List of paths to shielded cable test files
        unshielded_files: List of paths to unshielded cable test files
        save_dir: Directory to save the output plots
    """
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Set larger font sizes for all plots
    plt.rcParams.update({
        'font.size': 20,
        'axes.titlesize': 20,
        'axes.labelsize': 20,
        'xtick.labelsize': 20,
        'ytick.labelsize': 20,
        'legend.fontsize': 20,
        'figure.titlesize': 20,
    })
    
    # Create visualiser
    visualiser = TestDataVisualiser()
    
    # Load the test data
    shielded_data = []
    unshielded_data = []
    
    # Load shielded data
    for i, path in enumerate(shielded_files, 1):
        if not os.path.exists(path):
            print(f"Error: Shielded file '{path}' not found!")
            continue
        try:
            data = visualiser.load_csv_data(path)
            # Add a label for the plot
            data['label'] = f"Shielded-{i}"
            data['type'] = "shielded"
            shielded_data.append(data)
            print(f"Successfully loaded: {path} as Shielded-{i}")
        except Exception as e:
            print(f"Error loading {path}: {e}")
    
    # Load unshielded data
    for i, path in enumerate(unshielded_files, 1):
        if not os.path.exists(path):
            print(f"Error: Unshielded file '{path}' not found!")
            continue
        try:
            data = visualiser.load_csv_data(path)
            # Add a label for the plot
            data['label'] = f"Unshielded-{i}"
            data['type'] = "unshielded"
            unshielded_data.append(data)
            print(f"Successfully loaded: {path} as Unshielded-{i}")
        except Exception as e:
            print(f"Error loading {path}: {e}")
    
    # Combine all test data
    all_data = shielded_data + unshielded_data
    
    if len(all_data) == 0:
        print("No valid test files were loaded!")
        return
    
    # Define colors for shielded and unshielded
    shielded_color = 'blue'
    unshielded_color = 'red'
    
    # Line styles to differentiate between tests of the same type
    line_styles = ['-', '--', '-.', ':']
    
    # 1. Response Time Line Plot
    print("Generating response time comparison plot...")
    fig, ax = plt.figure(figsize=(14, 9)), plt.gca()
    
    for i, test_data in enumerate(all_data):
        df = test_data["data"]
        success_df = df[df['Status'] == 'Success']
        
        # Choose color based on cable type
        color = shielded_color if test_data['type'] == 'shielded' else unshielded_color
        
        # Choose line style based on test number within the type
        if test_data['type'] == 'shielded':
            style_idx = shielded_data.index(test_data) % len(line_styles)
        else:
            style_idx = unshielded_data.index(test_data) % len(line_styles)
            
        line_style = line_styles[style_idx]
        
        # Plot with consistent color for each type
        ax.plot(success_df['Attempt'], success_df['Response Time (ms)'], 
                marker='o', markersize=4, linestyle=line_style, 
                color=color, label=test_data['label'], linewidth=2)
    
    ax.set_xlabel('Packet Number', fontsize=20)
    ax.set_ylabel('Response Time (ms)', fontsize=20)
    ax.set_title('Response Time Comparison - 325V, 120° Conduction Angle', fontsize=24, fontweight='bold')
    ax.legend(fontsize=20)
    ax.grid(True, alpha=0.3)
    
    # Make tick labels larger
    plt.setp(ax.get_xticklabels(), fontsize=20)
    plt.setp(ax.get_yticklabels(), fontsize=20)

    # Add more space at the bottom for the title
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig(f"{save_dir}/response_time_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Box Plot with consistent colors
    print("Generating box plot comparison...")
    fig, ax = plt.figure(figsize=(14, 9)), plt.gca()
    
    # Prepare data for boxplot
    response_times_data = []
    labels = []
    colors = []
    
    # First add shielded data
    for test_data in shielded_data:
        df = test_data["data"]
        success_df = df[df['Status'] == 'Success']
        response_times_data.append(success_df['Response Time (ms)'].values)
        labels.append(test_data['label'])
        colors.append(shielded_color)
    
    # Then add unshielded data
    for test_data in unshielded_data:
        df = test_data["data"]
        success_df = df[df['Status'] == 'Success']
        response_times_data.append(success_df['Response Time (ms)'].values)
        labels.append(test_data['label'])
        colors.append(unshielded_color)
    
    # Create box plot
    boxes = ax.boxplot(response_times_data, labels=labels, patch_artist=True)
    
    # Set box colors
    for i, box in enumerate(boxes['boxes']):
        box.set(facecolor=colors[i], alpha=0.7, linewidth=2)
    
    # Make median lines thicker and black
    for median in boxes['medians']:
        median.set(color='black', linewidth=2)
    
    # Make whiskers and caps thicker
    for whisker in boxes['whiskers']:
        whisker.set(linewidth=2)
    for cap in boxes['caps']:
        cap.set(linewidth=2)
    
    ax.set_ylabel('Response Time (ms)', fontsize=16)
    ax.set_title('Response Time Distribution - 325V, 120° Conduction Angle', fontsize=18, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Rotate x-labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=14)
    
    # Add a legend manually
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=shielded_color, alpha=0.7, label='Shielded'),
        Patch(facecolor=unshielded_color, alpha=0.7, label='Unshielded')
    ]
    ax.legend(handles=legend_elements, fontsize=14)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig(f"{save_dir}/boxplot_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Statistical Summary
    print("Generating statistical summary...")
    stats_data = []
    
    # First add shielded stats
    for test_data in shielded_data:
        df = test_data["data"]
        metadata = test_data["metadata"]
        success_df = df[df['Status'] == 'Success']
        response_times = success_df['Response Time (ms)']
        
        stats_data.append({
            'Test': test_data['label'],
            'Cable Type': 'Shielded',
            'Mean (ms)': round(response_times.mean(), 2),
            'Median (ms)': round(response_times.median(), 2),
            'Min (ms)': round(response_times.min(), 2),
            'Max (ms)': round(response_times.max(), 2),
            'Std Dev (ms)': round(response_times.std(), 2),
            'Lost Packets': metadata.get('Lost Packets', 'N/A'),
            'Loss %': metadata.get('Loss %', 'N/A')
        })
    
    # Then add unshielded stats
    for test_data in unshielded_data:
        df = test_data["data"]
        metadata = test_data["metadata"]
        success_df = df[df['Status'] == 'Success']
        response_times = success_df['Response Time (ms)']
        
        stats_data.append({
            'Test': test_data['label'],
            'Cable Type': 'Unshielded',
            'Mean (ms)': round(response_times.mean(), 2),
            'Median (ms)': round(response_times.median(), 2),
            'Min (ms)': round(response_times.min(), 2),
            'Max (ms)': round(response_times.max(), 2),
            'Std Dev (ms)': round(response_times.std(), 2),
            'Lost Packets': metadata.get('Lost Packets', 'N/A'),
            'Loss %': metadata.get('Loss %', 'N/A')
        })
    
    stats_df = pd.DataFrame(stats_data)
    
    # Save stats to CSV
    stats_df.to_csv(f"{save_dir}/cable_type_comparison_stats.csv", index=False)
    
    # 4. Bar chart comparison of means
    print("Generating bar chart comparison...")
    fig, ax = plt.figure(figsize=(14, 9)), plt.gca()
    
    # Extract data for the bar chart
    shielded_means = [data['Mean (ms)'] for data in stats_data if data['Cable Type'] == 'Shielded']
    unshielded_means = [data['Mean (ms)'] for data in stats_data if data['Cable Type'] == 'Unshielded']
    
    # Plot grouped bar chart
    bar_width = 0.35
    x = np.arange(max(len(shielded_means), len(unshielded_means)))
    
    # Plot bars
    shielded_bars = ax.bar(x - bar_width/2, shielded_means, bar_width, label='Shielded', color=shielded_color, alpha=0.7)
    unshielded_bars = ax.bar(x + bar_width/2, unshielded_means, bar_width, label='Unshielded', color=unshielded_color, alpha=0.7)
    
    ax.set_xlabel('Test Number', fontsize=20)
    ax.set_ylabel('Mean Response Time (ms)', fontsize=20)
    ax.set_title('Mean Response Time Comparison - 325V, 120° Conduction Angle', fontsize=24, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Test {i+1}' for i in range(len(x))], fontsize=20)
    ax.legend(fontsize=20, frameon=True, framealpha=1.0,
                  facecolor='white', edgecolor='black')
    ax.grid(True, alpha=0.3)
    
    # Make tick labels larger
    plt.setp(ax.get_xticklabels(), fontsize=20)
    plt.setp(ax.get_yticklabels(), fontsize=20)
    
    # Add value labels on top of bars
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=20)
    
    add_value_labels(shielded_bars)
    add_value_labels(unshielded_bars)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig(f"{save_dir}/mean_comparison_bar_chart.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Print a summary
    print("\nComparison complete! Files saved to:")
    print(f"  {os.path.abspath(save_dir)}/")
    print("\nStatistical Summary:")
    print(stats_df.to_string(index=False))
    
    print("\nOpen the PNG files in your image viewer to see the plots")
    return stats_df

if __name__ == "__main__":
    # Parse arguments to get shielded and unshielded files
    shielded_files = []
    unshielded_files = []
    
    # Allow the script to run with defaults if no arguments provided
    if len(sys.argv) > 1:
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == '--shielded':
                i += 1
                while i < len(sys.argv) and not sys.argv[i].startswith('--'):
                    shielded_files.append(sys.argv[i])
                    i += 1
            elif sys.argv[i] == '--unshielded':
                i += 1
                while i < len(sys.argv) and not sys.argv[i].startswith('--'):
                    unshielded_files.append(sys.argv[i])
                    i += 1
            else:
                i += 1
    
    # Use correct default files from high_power_120deg directories
    if not unshielded_files:
        unshielded_files = [
            "results/lan/cable/unshielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0018.csv",
            "results/lan/cable/unshielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0019.csv",
            "results/lan/cable/unshielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0020.csv"
        ]
    
    if not shielded_files:
        shielded_files = [
            "results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0021.csv",
            "results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0022.csv",
            "results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0023.csv"
        ]
    
    # Check if files exist
    missing_files = []
    for file_path in shielded_files + unshielded_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("Warning: The following files were not found:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        
        # List available files to help user
        print("\nAvailable CSV files in the expected directories:")
        for directory in ["results/lan/cable/shielded/high_power_120deg", "results/lan/cable/unshielded/High_power_120deg"]:
            if os.path.exists(directory):
                files = [f for f in os.listdir(directory) if f.endswith('.csv')]
                if files:
                    print(f"\n{directory}:")
                    for file in files:
                        print(f"  - {file}")
                else:
                    print(f"\n{directory}: No CSV files found")
            else:
                print(f"\n{directory}: Directory not found")
    else:
        print(f"Comparing {len(shielded_files)} shielded tests with {len(unshielded_files)} unshielded tests")
        compare_cable_types(shielded_files, unshielded_files)