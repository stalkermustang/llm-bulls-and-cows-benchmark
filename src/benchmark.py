import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Dict, List, Tuple

import numpy as np
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .game import BullsAndCowsGame
from .llm_player import LLMPlayer


@dataclass
class GameProgress:
    total_turns: int = 0
    completed_games: int = 0
    successful_games: int = 0
    format_failures: int = 0
    active_games: Dict[int, str] = None  # game_idx -> current_state
    lock: Lock = Lock()

    def __post_init__(self):
        if self.active_games is None:
            self.active_games = {}


class BenchmarkRunner:
    def __init__(self, config: Dict):
        self.config = config
        self.progress = GameProgress()
        # Choose spinner style once at initialization
        spinner_styles = ["earth", "monkey", "moon", "clock", "smiley"]
        self.progress_spinner = Spinner(random.choice(spinner_styles))

        if self.config["output"]["results_dir"]:
            from .logger import BenchmarkLogger

            run_id = None
            if "run_id" in self.config["output"]:
                run_id = self.config["output"]["run_id"]
                potential_path = os.path.join(
                    self.config["output"]["results_dir"], f"benchmark_{run_id}"
                )
                if os.path.exists(os.path.join(potential_path)):
                    raise ValueError(
                        "The benchmark results with the same `run_id` are already reported. Please change `run_id`!"
                    )
            self.logger = BenchmarkLogger(self.config["output"]["results_dir"], run_id)
            self.logger.log_config(self.config)
        else:
            self.logger = None

    def _run_single_game(self, config: Dict, game_idx: int = 0) -> Dict:
        """Run a single game with real-time progress updates."""
        player = LLMPlayer(config)
        game = BullsAndCowsGame(
            length=config["benchmark"]["target_length"],
            allow_repeating=config["benchmark"]["allow_repeating_digits"],
        )
        history: List[Tuple[str, Tuple[int, int]]] = []
        cur_game_format_failures = 0
        target = game.get_target()

        with self.progress.lock:
            self.progress.active_games[game_idx] = f"Starting game (target: {target})"

        if self.logger:
            self.logger.log_game_start(game_idx, target)

        def update_progress(status: str):
            with self.progress.lock:
                self.progress.active_games[game_idx] = status

        cur_game_turn = 0
        failure_reason = None
        while cur_game_turn < config["benchmark"]["max_turns"]:
            # Try to get a valid guess, with error feedback if needed
            last_error = False
            guess = None

            # We'll give the model up to 3 attempts to provide a valid guess
            for attempt_idx in range(3):
                # handle the situation when we reach the bound with wrong formatting
                if cur_game_turn == config["benchmark"]["max_turns"]:
                    guess = None
                    failure_reason = "max_turns_exceeded"
                    break
                guess = player.get_next_guess(game, history, last_error)
                # Count each LLM response as a turn
                cur_game_turn += 1

                with self.progress.lock:
                    self.progress.total_turns += 1
                    if guess is None:
                        cur_game_format_failures += 1
                        self.progress.format_failures += 1

                update_progress(f"Turn {cur_game_turn} completed (target: {target})")

                if guess is not None:
                    break

                last_error = True

            if guess is None:
                with self.progress.lock:
                    self.progress.completed_games += 1
                    self.progress.active_games.pop(game_idx, None)

                result = {
                    "success": False,
                    "target": target,
                    "total_turns": cur_game_turn,
                    "format_failures": cur_game_format_failures,
                    "history": history,
                    "failure_reason": failure_reason or "invalid_format_after_retries",
                }
                if self.logger:
                    self.logger.log_game_end(game_idx, result)
                return result

            result = game.make_guess(guess)
            history.append((guess, result))

            if self.logger:
                self.logger.log_game_turn(game_idx, cur_game_turn, guess, result)
                if self.config["output"]["save_full_conversations"]:
                    self.logger.log_conversation(game_idx, player.get_conversation_state())

            if game.is_won(result[0], result[1]):
                with self.progress.lock:
                    self.progress.completed_games += 1
                    self.progress.successful_games += 1
                    self.progress.active_games.pop(game_idx, None)

                result = {
                    "success": True,
                    "target": target,
                    "total_turns": cur_game_turn,
                    "format_failures": cur_game_format_failures,
                    "history": history,
                    "failure_reason": None,
                }
                if self.logger:
                    self.logger.log_game_end(game_idx, result)
                return result

        with self.progress.lock:
            self.progress.completed_games += 1
            self.progress.active_games.pop(game_idx, None)

        result = {
            "success": False,
            "target": target,
            "total_turns": config["benchmark"]["max_turns"],
            "format_failures": cur_game_format_failures,
            "history": history,
            "failure_reason": "max_turns_exceeded",
        }
        if self.logger:
            self.logger.log_game_end(game_idx, result)
        return result

    def _generate_status(self) -> Table:
        """Generate a rich table with current benchmark status."""
        table = Table(show_header=False, expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        with self.progress.lock:
            # Add overall progress
            total_games = self.config["benchmark"]["num_games"]
            progress_pct = (self.progress.completed_games / total_games) * 100
            table.add_row(
                "Overall Progress",
                f"{self.progress.completed_games}/{total_games} games ({progress_pct:.1f}%)",
            )

            # Add success stats if any games completed
            if self.progress.completed_games > 0:
                success_rate = (
                    self.progress.successful_games / self.progress.completed_games
                ) * 100
                table.add_row(
                    "Success Rate",
                    f"{self.progress.successful_games}/{self.progress.completed_games} games ({success_rate:.1f}%)",
                )
            else:
                table.add_row("Success Rate", f"0/0 games (N/A%)")

            # Add turn stats
            total_games_with_turns = self.progress.completed_games + len(self.progress.active_games)
            avg_turns = self.progress.total_turns / max(1, total_games_with_turns)
            table.add_row(
                "Total Turns", f"{self.progress.total_turns} (avg {avg_turns:.1f} per game)"
            )

            # Add format failure stats
            if self.progress.total_turns > 0:
                failure_rate = (self.progress.format_failures / self.progress.total_turns) * 100
                table.add_row(
                    "Format Failures",
                    f"{self.progress.format_failures}/{self.progress.total_turns} turns ({failure_rate:.1f}%)",
                )
            else:
                table.add_row("Format Failures", "0/0 turns (N/A%)")

            # Add active games with spinner
            if self.progress.active_games:
                table.add_section()
                current_time = time.time()
                active_text = Text()
                active_text.append("Active Games ")
                active_text.append(self.progress_spinner.render(current_time))
                table.add_row(active_text)
                for game_idx, status in sorted(self.progress.active_games.items()):
                    table.add_row(f"Game {game_idx}", f"[yellow]{status}[/yellow]")

        return table

    def run_benchmark(self) -> Dict:
        n_jobs = min(
            self.config["benchmark"]["num_concurrent_games"], self.config["benchmark"]["num_games"]
        )  # Limit max parallel jobs
        results = []

        with ThreadPoolExecutor(max_workers=n_jobs) as executor:
            # Submit all tasks
            futures = [
                executor.submit(self._run_single_game, self.config, i)
                for i in range(self.config["benchmark"]["num_games"])
            ]

            # Process results with rich live display
            with Live(self._generate_status(), refresh_per_second=4) as live:
                remaining_futures = futures.copy()

                while remaining_futures:
                    # Update display
                    live.update(self._generate_status())

                    # Collect completed results
                    newly_done = [f for f in remaining_futures if f.done()]
                    for future in newly_done:
                        results.append(future.result())
                        remaining_futures.remove(future)

                # Final update
                live.update(self._generate_status())

        successful_games = [r for r in results if r["success"]]
        total_turns = sum(r["total_turns"] for r in results)
        total_format_failures = sum(r["format_failures"] for r in results)

        turns_to_win = [r["total_turns"] for r in successful_games]

        metrics = {
            "success_rate": len(successful_games) / len(results) * 100,
            "successful_games": len(successful_games),
            "format_failure_rate": (
                (total_format_failures / total_turns * 100) if total_turns > 0 else 100
            ),
            "avg_turns": float(np.mean(turns_to_win)) if turns_to_win else 0,
            "std_turns": float(np.std(turns_to_win)) if turns_to_win else 0,
            "total_turns": total_turns,
            "total_format_failures": total_format_failures,
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.logger:
            self.logger.log_metrics(metrics)

        return metrics
