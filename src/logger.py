import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class BenchmarkLogger:
    def __init__(self, output_dir: str, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, f"benchmark_{self.run_id}")
        os.makedirs(self.output_dir, exist_ok=True)

        # Main event log file
        self.main_log_path = os.path.join(self.output_dir, "run.log")

        # Results file that contains config, metrics and game results
        self.results_file = os.path.join(self.output_dir, "results.json")
        self.results = {"config": None, "metrics": None, "games": []}

        # Conversations file that contains all game conversations
        self.conversations_file = os.path.join(self.output_dir, "full_conversations.json")
        self.conversations = {"game_id": dict()}  # dict of dicts with messages

    def log_config(self, config: Dict) -> None:
        self.results["config"] = config
        self._append_to_main_log("Configuration saved")

    def log_metrics(self, metrics: Dict) -> None:
        self.results["metrics"] = metrics
        self._append_to_main_log(f"Final metrics: {json.dumps(metrics, indent=2)}")

        # Save final results and conversations
        with open(self.results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        if len(self.conversations["game_id"]) > 0:
            with open(self.conversations_file, "w") as f:
                json.dump(self.conversations, f, indent=2)

    def log_game_start(self, game_idx: int, target: str) -> None:
        self._append_to_main_log(f"Game {game_idx} started with target {target}")

    def log_game_turn(self, game_idx: int, turn: int, guess: str, result: tuple) -> None:
        self._append_to_main_log(f"Game {game_idx} - Turn {turn}: Guess={guess}, Result={result}")

    def log_game_end(self, game_idx: int, result: Dict) -> None:
        status = "won" if result["success"] else f"failed ({result['failure_reason']})"
        self._append_to_main_log(
            f"Game {game_idx} {status} after {result['total_turns']} turns. "
            f"Format failures: {result['format_failures']}"
        )
        # Store game result for final results file
        self.results["games"].append(result)

    def log_conversation(self, game_idx: int, conversation_state: Dict) -> None:
        # Store latest conversation state for this game
        self.conversations["game_id"][game_idx] = conversation_state["messages"]

    def log_error(self, game_idx: int, error: str) -> None:
        self._append_to_main_log(f"Game {game_idx} error: {error}")

    def _append_to_main_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.main_log_path, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
