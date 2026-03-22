#!/usr/bin/env python3
"""
MedGuide-ROS — Experiment Results Analyser.

Reads CSV output from mission_logger, computes performance metrics,
runs statistical comparisons, and generates publication-quality plots.

Usage:
    python3 experiments/analyze_results.py \\
        --tuned  logs/tuned_results.csv \\
        --strict logs/strict_results.csv \\
        --output docs/results/

Outputs:
    docs/results/summary_stats.txt
    docs/results/fig1_success_rate.png
    docs/results/fig2_duration_boxplot.png
    docs/results/fig3_distance_line.png
    docs/results/fig4_efficiency.png
"""

import argparse
import os
import sys
import csv
import warnings
from collections import defaultdict

# Suppress scipy/numpy version mismatch warning (scipy 1.8 on numpy 2.x)
warnings.filterwarnings('ignore', category=UserWarning, module='scipy')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ── Style ────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.dpi': 300,
})

COLORS = {
    'tuned':  '#10b981',   # Emerald green
    'strict': '#f59e0b',   # Amber
}
LABELS = {
    'tuned':  'Config A — Tuned (0.18 m)',
    'strict': 'Config B — Strict (0.25 m)',
}


# ── Data Loading ─────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    """Load a mission_logger CSV file into a list of row dicts."""
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'trial':          int(row['trial']),
                'mission_id':     row['mission_id'],
                'goal_name':      row['goal_name'],
                'success':        row['success'].lower() == 'true',
                'duration_sec':   float(row['duration_sec']),
                'distance_m':     float(row['distance_m']),
                'straight_line_m': float(row.get('straight_line_m', 0)),
                'timestamp':      row.get('timestamp', ''),
            })
    return rows


def group_by_trial(rows: list) -> dict:
    """Group goal rows by trial number."""
    trials = defaultdict(list)
    for r in rows:
        trials[r['trial']].append(r)
    return dict(trials)


# ── Metric Computation ───────────────────────────────────────────────

def compute_trial_metrics(trial_rows: list[dict]) -> dict:
    """Compute per-trial aggregate metrics."""
    total = len(trial_rows)
    succeeded = sum(1 for r in trial_rows if r['success'])
    duration = sum(r['duration_sec'] for r in trial_rows)
    distance = sum(r['distance_m'] for r in trial_rows)
    sl = sum(r['straight_line_m'] for r in trial_rows if r['straight_line_m'] > 0)

    return {
        'total_goals': total,
        'succeeded':   succeeded,
        'success_rate': succeeded / total * 100 if total else 0,
        'duration_sec': duration,
        'distance_m':   distance,
        'efficiency':   (sl / distance * 100) if distance > 0.01 else 0,
    }


def summarise(label: str, rows: list[dict]) -> dict:
    """Full statistical summary for one configuration."""
    trials = group_by_trial(rows)
    metrics = [compute_trial_metrics(v) for v in trials.values()]

    sr   = [m['success_rate'] for m in metrics]
    dur  = [m['duration_sec'] for m in metrics]
    dist = [m['distance_m']   for m in metrics]
    eff  = [m['efficiency']   for m in metrics]

    return {
        'label':    label,
        'n_trials': len(trials),
        'n_goals':  len(rows),

        'success_rate': {'mean': np.mean(sr),  'std': np.std(sr),  'raw': sr},
        'duration':     {'mean': np.mean(dur), 'std': np.std(dur), 'raw': dur},
        'distance':     {'mean': np.mean(dist),'std': np.std(dist),'raw': dist},
        'efficiency':   {'mean': np.mean(eff), 'std': np.std(eff), 'raw': eff},
    }


# ── Statistical Tests ────────────────────────────────────────────────

def compare(a: list[float], b: list[float], name: str) -> str:
    """Run Mann-Whitney U + Cohen's d, return formatted result."""
    stat, p = stats.mannwhitneyu(a, b, alternative='two-sided')
    mean_a, mean_b = np.mean(a), np.mean(b)
    pooled_std = np.sqrt((np.std(a)**2 + np.std(b)**2) / 2)
    d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0
    sig = "✅ p < 0.05 (significant)" if p < 0.05 else "⚠ p ≥ 0.05 (not significant)"
    return (
        f"{name}:\n"
        f"  A: {mean_a:.2f}  B: {mean_b:.2f}  Δ={mean_a-mean_b:.2f}\n"
        f"  Mann-Whitney U={stat:.1f}, p={p:.4f}  {sig}\n"
        f"  Cohen's d = {d:.3f}\n"
    )


# ── Plots ────────────────────────────────────────────────────────────

def plot_success_rate(s_a: dict, s_b: dict, out: str):
    """Bar chart comparing mean success rates with error bars."""
    fig, ax = plt.subplots(figsize=(7, 5))
    configs = [LABELS['tuned'], LABELS['strict']]
    means   = [s_a['success_rate']['mean'], s_b['success_rate']['mean']]
    stds    = [s_a['success_rate']['std'],  s_b['success_rate']['std']]
    colors  = [COLORS['tuned'], COLORS['strict']]

    bars = ax.bar(configs, means, yerr=stds, capsize=6,
                  color=colors, edgecolor='black', linewidth=0.8, alpha=0.85)
    ax.set_ylabel('Mission Success Rate (%)')
    ax.set_title('Fig. 1 — Mission Success Rate by Configuration')
    ax.set_ylim(0, 110)
    ax.axhline(100, color='grey', linestyle='--', linewidth=0.7, label='Perfect')

    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f'{mean:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f'  Saved: {out}')


def plot_duration_boxplot(s_a: dict, s_b: dict, out: str):
    """Box plot of mission durations per configuration."""
    fig, ax = plt.subplots(figsize=(7, 5))
    data = [s_a['duration']['raw'], s_b['duration']['raw']]
    bp = ax.boxplot(data, patch_artist=True, notch=False,
                    medianprops={'color': 'black', 'linewidth': 2})
    for patch, color in zip(bp['boxes'], [COLORS['tuned'], COLORS['strict']]):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax.set_xticklabels([LABELS['tuned'], LABELS['strict']])
    ax.set_ylabel('Mission Duration (s)')
    ax.set_title('Fig. 2 — Mission Duration Distribution')
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f'  Saved: {out}')


def plot_distance_line(s_a: dict, s_b: dict, out: str):
    """Line plot of total path distance per trial."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for key, s in [('tuned', s_a), ('strict', s_b)]:
        y = s['distance']['raw']
        x = range(1, len(y) + 1)
        ax.plot(x, y, marker='o', label=LABELS[key],
                color=COLORS[key], linewidth=1.8, markersize=5)
        ax.axhline(np.mean(y), linestyle='--', color=COLORS[key],
                   alpha=0.5, linewidth=1)

    ax.set_xlabel('Trial Index')
    ax.set_ylabel('Total Path Distance (m)')
    ax.set_title('Fig. 3 — Path Distance per Trial')
    ax.legend()
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f'  Saved: {out}')


def plot_efficiency(s_a: dict, s_b: dict, out: str):
    """Bar chart of path efficiency (straight-line vs actual)."""
    fig, ax = plt.subplots(figsize=(7, 5))
    configs = [LABELS['tuned'], LABELS['strict']]
    means   = [s_a['efficiency']['mean'], s_b['efficiency']['mean']]
    stds    = [s_a['efficiency']['std'],  s_b['efficiency']['std']]
    colors  = [COLORS['tuned'], COLORS['strict']]

    ax.bar(configs, means, yerr=stds, capsize=6,
           color=colors, edgecolor='black', linewidth=0.8, alpha=0.85)
    ax.set_ylabel('Path Efficiency (%)')
    ax.set_title('Fig. 4 — Path Efficiency (Straight-Line vs Actual)')
    ax.set_ylim(0, 110)
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f'  Saved: {out}')


# ── Report ───────────────────────────────────────────────────────────

def write_summary(s_a: dict, s_b: dict, out: str):
    """Write a plain-text statistical summary report."""
    lines = [
        '═══════════════════════════════════════════════════════',
        '  MedGuide-ROS — Experiment Statistical Summary',
        '═══════════════════════════════════════════════════════',
        '',
        f'Config A (Tuned 0.18m)  — N={s_a["n_trials"]} trials, {s_a["n_goals"]} goals',
        f'Config B (Strict 0.25m) — N={s_b["n_trials"]} trials, {s_b["n_goals"]} goals',
        '',
        '─── Descriptive Statistics ────────────────────────────',
        f'{"Metric":<25} {"Config A μ±σ":>18} {"Config B μ±σ":>18}',
        f'{"─"*62}',
    ]

    for key, label, unit in [
        ('success_rate', 'Success Rate',      '%'),
        ('duration',     'Mission Duration',  's'),
        ('distance',     'Path Distance',     'm'),
        ('efficiency',   'Path Efficiency',   '%'),
    ]:
        a_m, a_s = s_a[key]['mean'], s_a[key]['std']
        b_m, b_s = s_b[key]['mean'], s_b[key]['std']
        lines.append(
            f'{label+" ("+unit+")":<25} {a_m:>8.2f} ±{a_s:>6.2f}   '
            f'{b_m:>8.2f} ±{b_s:>6.2f}'
        )

    lines += ['', '─── Statistical Tests (Mann-Whitney U) ────────────────']
    for key, name in [
        ('success_rate', 'Success Rate (%)'),
        ('duration',     'Mission Duration (s)'),
        ('distance',     'Path Distance (m)'),
        ('efficiency',   'Path Efficiency (%)'),
    ]:
        lines.append(compare(s_a[key]['raw'], s_b[key]['raw'], name))

    lines += [
        '═══════════════════════════════════════════════════════',
        'Interpretation guidance:',
        '  • Cohen\'s d < 0.2 = negligible effect',
        '  • Cohen\'s d 0.2–0.5 = small, 0.5–0.8 = medium, > 0.8 = large',
        '═══════════════════════════════════════════════════════',
    ]

    with open(out, 'w') as f:
        f.write('\n'.join(lines))
    print(f'  Saved: {out}')


# ── Main ─────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Analyse MedGuide experiment CSVs')
    p.add_argument('--tuned',  required=True, help='CSV for Config A (tuned 0.18m)')
    p.add_argument('--strict', required=True, help='CSV for Config B (strict 0.25m)')
    p.add_argument('--output', default='docs/results/', help='Output directory')
    args = p.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f'Loading Config A: {args.tuned}')
    rows_a = load_csv(args.tuned)
    print(f'Loading Config B: {args.strict}')
    rows_b = load_csv(args.strict)

    s_a = summarise('tuned',  rows_a)
    s_b = summarise('strict', rows_b)

    print('\nGenerating plots...')
    plot_success_rate  (s_a, s_b, os.path.join(args.output, 'fig1_success_rate.png'))
    plot_duration_boxplot(s_a, s_b, os.path.join(args.output, 'fig2_duration_boxplot.png'))
    plot_distance_line (s_a, s_b, os.path.join(args.output, 'fig3_distance_line.png'))
    plot_efficiency    (s_a, s_b, os.path.join(args.output, 'fig4_efficiency.png'))

    summary_path = os.path.join(args.output, 'summary_stats.txt')
    write_summary(s_a, s_b, summary_path)

    print(f'\n✅ Analysis complete. Results in: {args.output}')
    print(f'   View summary: cat {summary_path}')


if __name__ == '__main__':
    main()
