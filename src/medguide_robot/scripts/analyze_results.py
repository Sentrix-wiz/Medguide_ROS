#!/usr/bin/env python3
"""
Analyze experiment CSV results and generate comparison charts.

Usage:
    python3 scripts/analyze_results.py logs/baseline.csv logs/condB.csv

Or with labels:
    python3 scripts/analyze_results.py \
      --labels Baseline,Inflation,Velocity,Planner \
      logs/baseline.csv logs/inflation.csv logs/velocity.csv logs/planner.csv
"""

import argparse
import os
import sys

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError:
    print("Install dependencies: pip3 install pandas matplotlib")
    sys.exit(1)


def analyze(csv_paths, labels, output_dir):
    """Load CSVs, compute stats, print table, save chart."""
    results = []

    for path, label in zip(csv_paths, labels):
        if not os.path.exists(path):
            print(f"WARNING: {path} not found, skipping")
            continue

        df = pd.read_csv(path)
        total = len(df)
        ok = df[df['success'] == True]  # noqa: E712
        failed = total - len(ok)

        stats = {
            'Condition': label,
            'Goals': total,
            'Success %': round(ok.shape[0] / total * 100, 1) if total else 0,
            'Avg Time (s)': round(ok['duration_sec'].mean(), 1) if len(ok) else 0,
            'Std Time': round(ok['duration_sec'].std(), 1) if len(ok) > 1 else 0,
            'Avg Dist (m)': round(ok['distance_m'].mean(), 2) if len(ok) else 0,
            'Failed': failed,
        }
        results.append(stats)
        print(f"\n{'=' * 40}")
        print(f"  {label} ({path})")
        print(f"{'=' * 40}")
        print(f"  Goals:        {total}")
        print(f"  Succeeded:    {len(ok)}")
        print(f"  Failed:       {failed}")
        print(f"  Success rate: {stats['Success %']}%")
        print(f"  Avg time:     {stats['Avg Time (s)']}s ± {stats['Std Time']}s")
        print(f"  Avg distance: {stats['Avg Dist (m)']}m")

    if len(results) < 2:
        print("\nNeed at least 2 CSV files to compare.")
        return

    # Comparison table
    summary = pd.DataFrame(results)
    print(f"\n{'=' * 60}")
    print("  COMPARISON TABLE")
    print(f"{'=' * 60}")
    print(summary.to_string(index=False))

    # Improvement vs baseline
    base = results[0]
    print(f"\n  Improvement vs {base['Condition']}:")
    for r in results[1:]:
        time_diff = base['Avg Time (s)'] - r['Avg Time (s)']
        sign = '+' if time_diff > 0 else ''
        print(f"    {r['Condition']}: "
              f"success {r['Success %']}% vs {base['Success %']}%, "
              f"time {sign}{time_diff:.1f}s")

    # Generate chart
    os.makedirs(output_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    names = [r['Condition'] for r in results]
    colors = ['#2196F3', '#FF9800', '#4CAF50', '#E91E63'][:len(results)]

    # Success rate
    axes[0].bar(names, [r['Success %'] for r in results], color=colors)
    axes[0].set_ylabel('Success Rate (%)')
    axes[0].set_title('Goal Success Rate')
    axes[0].set_ylim(0, 105)

    # Duration
    axes[1].bar(names, [r['Avg Time (s)'] for r in results], color=colors)
    axes[1].set_ylabel('Time (seconds)')
    axes[1].set_title('Avg Goal Duration')

    # Distance
    axes[2].bar(names, [r['Avg Dist (m)'] for r in results], color=colors)
    axes[2].axhline(y=3.77, color='red', linestyle='--',
                    label='Straight-line avg')
    axes[2].set_ylabel('Distance (m)')
    axes[2].set_title('Avg Path Length')
    axes[2].legend()

    plt.suptitle('MedGuide-ROS Navigation Experiment Results',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    chart_path = os.path.join(output_dir, 'experiment_results.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    print(f"\n  Chart saved: {chart_path}")
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze MedGuide experiment results'
    )
    parser.add_argument(
        'csvs', nargs='+', help='CSV result files to compare'
    )
    parser.add_argument(
        '--labels', type=str, default=None,
        help='Comma-separated labels (default: filenames)'
    )
    parser.add_argument(
        '--output', type=str, default='docs',
        help='Output directory for charts'
    )
    args = parser.parse_args()

    if args.labels:
        labels = args.labels.split(',')
    else:
        labels = [os.path.splitext(os.path.basename(f))[0]
                  for f in args.csvs]

    analyze(args.csvs, labels, args.output)


if __name__ == '__main__':
    main()
