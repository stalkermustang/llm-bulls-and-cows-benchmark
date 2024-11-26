import argparse
import glob
import json
import os
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Bulls and Cows Benchmark Results</title>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"></script>
    <link href="https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css" rel="stylesheet">
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section {{
            margin-top: 30px;
        }}
        h1, h2 {{
            color: #2c3e50;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .run-info {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        #results-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        #results-table tbody tr.even {{
            background-color: #f8f9fa;
        }}
        #results-table tbody tr.odd {{
            background-color: white;
        }}
        #results-table tbody tr:hover {{
            background-color: #e9ecef;
        }}
        #results-table td:nth-child(4) {{
            font-weight: bold;
            background-color: #e3f2fd;
        }}
        #results-table th:nth-child(4) {{
            background-color: #bbdefb;
        }}
        .confidence-interval {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .dataTables_wrapper .dataTables_length,
        .dataTables_wrapper .dataTables_filter {{
            margin-bottom: 15px;
        }}
        .dataTables_wrapper .dataTables_info {{
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Bulls and Cows Benchmark Results</h1>
        <div class="run-info">
            {run_info_html}
        </div>
        <div class="section">
            <div class="chart-container">
                <div id="metrics_comparison"></div>
            </div>
            <div class="chart-container">
                <div id="turn_stats"></div>
            </div>
            <div class="chart-container">
                <div id="outcomes"></div>
            </div>
        </div>
    </div>
    <script>
        $(document).ready(function() {{
            $('#results-table').DataTable({{
                order: [[3, 'desc']], // Sort by success rate by default
                pageLength: 25,
                lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
                stripeClasses: ['odd', 'even'], // Ensure striping works
                columnDefs: [
                    {{
                        targets: [3, 4, 5], // Success Rate, Avg Turns, Format Failures
                        type: 'num',
                        searchable: false, // Disable search for numeric columns
                        render: function(data, type, row) {{
                            if (type === 'sort') {{
                                return parseFloat(data);
                            }}
                            return data;
                        }}
                    }},
                    {{
                        targets: [2], // Games column
                        searchable: false,
                        type: 'num'
                    }}
                ]
            }});
        }});
        {plotly_js}
    </script>
</body>
</html>"""


def calculate_confidence_interval(successes, total, confidence=0.95):
    """
    Calculate the Wilson score confidence interval for a proportion.

    Parameters:
    - successes (int): Number of successful outcomes.
    - total (int): Total number of experiments.
    - confidence (float): Confidence level (default is 0.95 for 95%).

    Returns:
    - tuple: Lower and upper bounds of the confidence interval.
    """
    if total == 0:
        return 0, 0

    p = successes / total
    z = stats.norm.ppf((1 + confidence) / 2)

    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    spread = z * ((p * (1 - p) + z**2 / (4 * total)) / total) ** 0.5 / denominator

    return max(0, center - spread), min(1, center + spread)


def load_benchmark_results(results_dir):
    results = []
    for benchmark_dir in glob.glob(os.path.join(results_dir, "benchmark_*")):
        try:
            results_file = os.path.join(benchmark_dir, "results.json")
            if not os.path.exists(results_file):
                continue

            with open(results_file) as f:
                data = json.load(f)

            results.append({"run_id": benchmark_dir, "data": data})
        except Exception as e:
            print(f"Error loading results from {benchmark_dir}: {e}")

    # Sort by success rate descending
    return sorted(
        results,
        key=lambda x: (x["data"]["metrics"]["success_rate"],),
        reverse=True,
    )


def create_run_info_table(results):
    """Create an HTML table with run information."""
    if not results:
        return "<p>No benchmark results found.</p>"

    html = """
    <table id="results-table">
        <thead>
            <tr>
                <th>Run ID</th>
                <th>Model</th>
                <th>Games</th>
                <th>Success Rate ↑</th>
                <th>Avg Turns (success only) ↓</th>
                <th>Format Failures ↓</th>
            </tr>
        </thead>
        <tbody>
    """

    for result in results:
        run_id = os.path.basename(result["run_id"])
        config = result["data"]["config"]
        metrics = result["data"]["metrics"]
        games = result["data"]["games"]

        # Calculate confidence interval
        successes = sum(1 for g in games if g["success"])
        total = len(games)
        ci_low, ci_high = calculate_confidence_interval(successes, total)
        ci_str = f" ({ci_low*100:.1f}% - {ci_high*100:.1f}%)"

        html += f"""
        <tr>
            <td>{run_id}</td>
            <td>{config['llm']['model']}</td>
            <td>{total}</td>
            <td data-sort="{metrics['success_rate']}">{metrics['success_rate']:.1f}%<span class="confidence-interval">{ci_str}</span></td>
            <td data-sort="{metrics['avg_turns']}">{metrics['avg_turns']:.1f} ± {metrics['std_turns']:.1f}</td>
            <td data-sort="{metrics['format_failure_rate']}">{metrics['format_failure_rate']:.1f}%</td>
        </tr>
        """

    html += """
        </tbody>
    </table>
    """
    return html


def create_metrics_comparison(results):
    """Create comparison charts for metrics across runs."""
    if not results:
        return None

    run_ids = [os.path.basename(r["run_id"]) for r in results]

    # Create figure
    fig = go.Figure()

    # Success Rate with confidence intervals
    success_rates = []
    ci_lower = []
    ci_upper = []

    for result in results:
        metrics = result["data"]["metrics"]
        games = result["data"]["games"]
        successes = sum(1 for g in games if g["success"])
        total = len(games)
        ci_low, ci_high = calculate_confidence_interval(successes, total)

        success_rates.append(metrics["success_rate"])
        ci_lower.append(ci_low * 100)
        ci_upper.append(ci_high * 100)

    fig.add_trace(
        go.Bar(
            name="Success Rate",
            x=run_ids,
            y=success_rates,
            marker_color="#2ecc71",
            error_y=dict(
                type="data",
                symmetric=False,
                array=[u - s for u, s in zip(ci_upper, success_rates)],
                arrayminus=[s - l for l, s in zip(ci_lower, success_rates)],
                visible=True,
            ),
        )
    )

    fig.update_layout(
        title={
            "text": "Success Rate by Run (with 95% CI)",
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": {"size": 20},
        },
        annotations=[
            {
                "text": "CI calculated using Wilson Score Interval",
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1.1,
                "showarrow": False,
                "font": {"size": 12, "color": "#7f8c8d"},
            }
        ],
        yaxis=dict(title="Success Rate (%)", range=[0, 100]),
        height=500,
        showlegend=True,
        hovermode="x unified",
    )

    return fig


def create_turn_stats_chart(results):
    """Create a chart showing turn statistics across runs."""
    if not results:
        return None

    run_ids = [os.path.basename(r["run_id"]) for r in results]

    fig = go.Figure()

    # Calculate statistics for successful games only
    for i, result in enumerate(results):
        success_games = [g for g in result["data"]["games"] if g["success"]]
        if success_games:
            turns = [g["total_turns"] for g in success_games]

            # Add violin plot
            fig.add_trace(
                go.Violin(
                    x=[run_ids[i]] * len(turns),
                    y=turns,
                    name=run_ids[i],
                    box_visible=True,
                    meanline_visible=True,
                    points="all",
                    pointpos=0,  # Center the points
                    jitter=0.1,  # Add some random spread to points
                    marker=dict(
                        color="rgba(231, 76, 60, 0.7)",  # Red dots with transparency
                        size=7,
                        line=dict(color="rgba(192, 57, 43, 1)", width=1),
                    ),
                    line_color="rgba(52, 152, 219, 0.8)",
                    fillcolor="rgba(52, 152, 219, 0.2)",
                    opacity=0.8,
                    side="both",
                    width=0.5,  # Even narrower violin
                    showlegend=False,
                )
            )

    fig.update_layout(
        title={
            "text": "Turn Statistics by Run (Success Only)",
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": {"size": 20},
        },
        yaxis_title="Number of Turns",
        height=500,
        showlegend=False,
        hovermode="closest",
        violinmode="group",
        annotations=[
            {
                "text": "Violin plots show distribution, points show individual games",
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1.1,
                "showarrow": False,
                "font": {"size": 12, "color": "#7f8c8d"},
            }
        ],
    )

    return fig


def create_outcomes_chart(results):
    """Create a chart showing game outcomes across runs."""
    if not results:
        return None

    run_ids = [os.path.basename(r["run_id"]) for r in results]

    # Calculate outcomes for each run
    success_pcts = []
    format_failure_pcts = []
    max_turns_pcts = []

    for result in results:
        games = result["data"]["games"]
        total = len(games)
        success_pcts.append(100 * sum(1 for g in games if g["success"]) / total)
        format_failure_pcts.append(
            100
            * sum(
                1
                for g in games
                if not g["success"] and g["failure_reason"] == "invalid_format_after_retries"
            )
            / total
        )
        max_turns_pcts.append(
            100
            * sum(
                1 for g in games if not g["success"] and g["failure_reason"] == "max_turns_exceeded"
            )
            / total
        )

    fig = go.Figure()

    # Calculate absolute numbers for hover text
    success_counts = []
    format_failure_counts = []
    max_turns_counts = []

    for result in results:
        games = result["data"]["games"]
        success_counts.append(sum(1 for g in games if g["success"]))
        format_failure_counts.append(
            sum(
                1
                for g in games
                if not g["success"] and g["failure_reason"] == "invalid_format_after_retries"
            )
        )
        max_turns_counts.append(
            sum(
                1 for g in games if not g["success"] and g["failure_reason"] == "max_turns_exceeded"
            )
        )

    # Add traces for each outcome type
    fig.add_trace(
        go.Bar(
            name="Success",
            x=run_ids,
            y=success_pcts,
            marker_color="#2ecc71",
            hovertemplate="%{y:.1f}% (%{customdata} games)<extra>Success</extra>",
            customdata=success_counts,
        )
    )

    fig.add_trace(
        go.Bar(
            name="Format Failure",
            x=run_ids,
            y=format_failure_pcts,
            marker_color="#e74c3c",
            hovertemplate="%{y:.1f}% (%{customdata} games)<extra>Format Failure</extra>",
            customdata=format_failure_counts,
        )
    )

    fig.add_trace(
        go.Bar(
            name="Max Turns",
            x=run_ids,
            y=max_turns_pcts,
            marker_color="#f1c40f",
            hovertemplate="%{y:.1f}% (%{customdata} games)<extra>Max Turns</extra>",
            customdata=max_turns_counts,
        )
    )

    fig.update_layout(
        title="Game Outcomes by Run",
        yaxis=dict(title="Percentage of Games", ticksuffix="%", range=[0, 100]),
        barmode="stack",
        height=500,
        showlegend=True,
        hovermode="x unified",
    )

    return fig


def create_markdown_table(results):
    """Create a markdown table with run information."""
    if not results:
        return "No benchmark results found."

    # Header
    md = "| Run ID | Model | Games | Success Rate | Avg Turns (success only) | Format Failures |\n"
    md += "|--------|--------|-------|--------------|------------------------|----------------|\n"

    for result in results:
        run_id = os.path.basename(result["run_id"])
        config = result["data"]["config"]
        metrics = result["data"]["metrics"]
        games = result["data"]["games"]

        # Calculate confidence interval
        successes = sum(1 for g in games if g["success"])
        total = len(games)
        ci_low, ci_high = calculate_confidence_interval(successes, total)
        ci_str = f"({ci_low*100:.1f}% - {ci_high*100:.1f}%)"

        md += f"| {run_id} | {config['llm']['model']} | {total} | {metrics['success_rate']:.1f}% {ci_str} | {metrics['avg_turns']:.1f} ± {metrics['std_turns']:.1f} | {metrics['format_failure_rate']:.1f}% |\n"

    return md


def create_visualization(results_dir, html_path, markdown_path):
    """
    Generate visualization and markdown table from benchmark results.

    Args:
        results_dir: Directory containing benchmark results
        html_path: Path to save the HTML visualization
        markdown_path: Path to save the markdown table
    """
    results = load_benchmark_results(results_dir)
    if not results:
        print("No results found!")
        return

    # Create run info table
    run_info_html = create_run_info_table(results)

    # Create comparison charts
    metrics_fig = create_metrics_comparison(results)
    turn_stats_fig = create_turn_stats_chart(results)
    outcomes_fig = create_outcomes_chart(results)

    # Generate plotly JS
    plotly_js = f"""
        Plotly.newPlot('metrics_comparison', {metrics_fig.to_json()});
        Plotly.newPlot('turn_stats', {turn_stats_fig.to_json()});
        Plotly.newPlot('outcomes', {outcomes_fig.to_json()});
    """

    # Generate HTML
    html_content = HTML_TEMPLATE.format(run_info_html=run_info_html, plotly_js=plotly_js)

    # Support both file paths and file-like objects
    if hasattr(html_path, "write"):
        html_path.write(html_content)
    else:
        with open(html_path, "w") as f:
            f.write(html_content)
            print(f"Visualization saved to {html_path}")

    if hasattr(markdown_path, "write"):
        markdown_path.write(html_content)
    else:
        with open(markdown_path, "w") as f:
            f.write("# Bulls and Cows Benchmark Results\n\n")
            f.write(create_markdown_table(results))
            print(f"Markdown table saved to {markdown_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate visualization for Bulls and Cows benchmark results"
    )

    default_res_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "benchmark_results/4_digits/"
    )

    parser.add_argument(
        "--results-dir", default=default_res_dir, help="Directory containing benchmark results"
    )
    parser.add_argument(
        "--output-dir", default=None, help="Directory to save the visualization files"
    )

    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = args.results_dir

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Define output paths
    html_path = os.path.join(args.output_dir, "visualization.html")
    markdown_path = os.path.join(args.output_dir, "results_table.md")

    create_visualization(args.results_dir, html_path, markdown_path)
