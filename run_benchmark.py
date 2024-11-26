import argparse
import os
from typing import Dict, Optional

import yaml
from dotenv import load_dotenv

from src.benchmark import BenchmarkRunner

load_dotenv()


def load_config(config_path: str) -> Dict:
    """Load configuration from a YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def display_results(config: Dict, metrics: Dict) -> None:
    """Display benchmark results in a formatted table."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Create results table
    table = Table(show_header=False, title="Benchmark Results", expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Add metrics
    table.add_row(
        "Success Rate",
        f"{metrics['success_rate']:.2f}% ({metrics['successful_games']} out of {config['benchmark']['num_games']} games)",
    )
    table.add_row(
        "Format Failure Rate",
        f"{metrics['format_failure_rate']:.2f}% ({metrics['total_format_failures']} out of {metrics['total_turns']} turns)",
    )
    if metrics["avg_turns"] is not None:
        table.add_row(
            "Average Turns to Win", f"{metrics['avg_turns']:.2f} ± {metrics['std_turns']:.2f}"
        )
    else:
        table.add_row("Average Turns to Win", "[yellow]N/A (no successful games)[/yellow]")

    # Display results in a panel
    console.print()
    console.print(Panel(table, border_style="blue"))


def main(config: Dict) -> Dict:
    """Run the benchmark with the provided or default configuration.

    Args:
        config: a configuration dictionary, with main fields
            llm: to set up LLM with sampling params (LiteLLM is used)
            benchmark: to manage testing parameters
            output: to manage logging

    Returns:
        The metrics dictionary from the benchmark run.
    """
    runner = BenchmarkRunner(config)
    metrics = runner.run_benchmark()

    display_results(config, metrics)
    return metrics


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Bulls and Cows benchmark")
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join("config", "default_config.yaml"),
        help="Path to the configuration file (default: config/default_config.yaml)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    main(config)
