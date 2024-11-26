import io
import json
import os
from pathlib import Path

import pytest

from scripts.visualize_results import create_visualization, load_benchmark_results


def test_create_visualization():
    # Get the real benchmark results directory
    benchmark_dir = Path(__file__).parent.parent / "benchmark_results/4_digits"
    assert benchmark_dir.exists(), "Benchmark results directory not found"

    # Load one of the results files to get expected values
    results = load_benchmark_results(str(benchmark_dir))
    assert results, "No benchmark results found"

    # Get some values we expect to find in the visualization
    first_result = results[0]
    expected_model = first_result["data"]["config"]["llm"]["model"]
    expected_success_rate = f"{first_result['data']['metrics']['success_rate']:.1f}%"
    expected_avg_turns = f"{first_result['data']['metrics']['avg_turns']:.1f}"

    # Create an in-memory buffer for the HTML output
    html_output_buffer = io.StringIO()
    md_output_buffer = io.StringIO()

    # Call create_visualization with real benchmark data
    create_visualization(str(benchmark_dir), html_output_buffer, md_output_buffer)

    # Get the HTML content
    html_content = html_output_buffer.getvalue()

    # Basic validation of the HTML output
    assert "<!DOCTYPE html>" in html_content
    assert "<title>Bulls and Cows Benchmark Results</title>" in html_content
    assert expected_model in html_content  # Check real model name is included
    assert expected_success_rate in html_content  # Check real success rate is included
    assert expected_avg_turns in html_content  # Check real avg turns is included

    # Verify all plots are included
    assert "Plotly.newPlot('metrics_comparison'" in html_content
    assert "Plotly.newPlot('turn_stats'" in html_content
    assert "Plotly.newPlot('outcomes'" in html_content

    # Verify the table structure
    assert '<table id="results-table">' in html_content
    assert "<th>Run ID</th>" in html_content
    assert "<th>Model</th>" in html_content
    assert "<th>Games</th>" in html_content
    assert "<th>Success Rate ↑</th>" in html_content
