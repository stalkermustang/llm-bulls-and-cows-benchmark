import io
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from src.benchmark import BenchmarkRunner, GameProgress
from src.game import BullsAndCowsGame


class TestBenchmark(unittest.TestCase):
    def setUp(self):
        self.config = {
            "benchmark": {
                "num_games": 1,
                "max_turns": 10,
                "target_length": 4,
                "allow_repeating_digits": False,
                "num_concurrent_games": 4,
            },
            "output": {"results_dir": None},
        }

    def test_turn_counting(self):
        """Test that turns are counted correctly, counting invalid guesses as well."""
        runner = BenchmarkRunner(self.config)

        # Mock LLMPlayer to simulate different guess scenarios
        with patch("src.benchmark.LLMPlayer") as mock_player:
            player_instance = mock_player.return_value

            # First call returns None (invalid format)
            # Second call returns valid guess "1234"
            player_instance.get_next_guess.side_effect = [
                None,  # First attempt - invalid format
                "1234",  # Second attempt - valid guess
            ]

            # Mock the game to return a winning result (4, 0) for the valid guess
            with patch.object(BullsAndCowsGame, "make_guess", return_value=(4, 0)):
                with patch.object(BullsAndCowsGame, "get_target", return_value="1234"):
                    result = runner._run_single_game(self.config)

                    # Should only count the valid guess, not the invalid attempt
                    self.assertEqual(result["total_turns"], 2)
                    self.assertEqual(runner.progress.total_turns, 2)
                    self.assertEqual(result["format_failures"], 1)

    def test_turn_counting_with_multiple_valid_guesses(self):
        """Test turn counting with multiple valid guesses."""
        runner = BenchmarkRunner(self.config)

        with patch("src.benchmark.LLMPlayer") as mock_player:
            player_instance = mock_player.return_value

            # All valid guesses
            player_instance.get_next_guess.side_effect = [
                "1234",  # First turn
                "5678",  # Second turn
                "9012",  # Third turn
            ]

            # Mock game to return non-winning results for first two guesses,
            # then a winning result
            game_responses = [
                (0, 2),  # First guess - 2 cows (1 and 2)
                (0, 0),  # Second guess - no matches
                (4, 0),  # Third guess - all bulls (win)
            ]

            with patch.object(BullsAndCowsGame, "make_guess", side_effect=game_responses):
                with patch.object(BullsAndCowsGame, "get_target", return_value="9012"):
                    result = runner._run_single_game(self.config)

                    # Should count all three valid guesses
                    self.assertEqual(result["total_turns"], 3)
                    self.assertEqual(runner.progress.total_turns, 3)
                    self.assertEqual(result["format_failures"], 0)
                    self.assertTrue(result["success"])

    def test_average_turns_calculation(self):
        """Test that average turns are calculated correctly including active games."""
        runner = BenchmarkRunner(self.config)

        # Simulate some active games and turns
        runner.progress.total_turns = 10
        runner.progress.completed_games = 1
        runner.progress.active_games = {1: "active1", 2: "active2", 3: "active3"}  # 3 active games

        # Get the status table and render it to string
        table = runner._generate_status()
        console = Console(file=io.StringIO(), force_terminal=True)
        console.print(table)
        output = console.file.getvalue()

        # Find the line containing "Total Turns"
        total_turns_line = None
        for line in output.split("\n"):
            if "Total Turns" in line:
                total_turns_line = line
                break

        self.assertIsNotNone(total_turns_line, "Total Turns line not found in table")

        # Extract the average from the string like "10 (avg 2.5 per game)"
        row_text = total_turns_line
        avg_str = row_text[row_text.find("avg ") + 4 : row_text.find(" per")]
        avg_turns = float(avg_str)

        # With 10 turns and 4 total games (1 completed + 3 active),
        # the average should be 2.5
        self.assertEqual(avg_turns, 2.5)

        # Test with only active games (no completed)
        runner.progress.total_turns = 8
        runner.progress.completed_games = 0
        runner.progress.active_games = {1: "active1", 2: "active2"}  # 2 active games

        table = runner._generate_status()
        console = Console(file=io.StringIO(), force_terminal=True)
        console.print(table)
        output = console.file.getvalue()

        total_turns_line = None
        for line in output.split("\n"):
            if "Total Turns" in line:
                total_turns_line = line
                break

        self.assertIsNotNone(total_turns_line, "Total Turns line not found in table")
        row_text = total_turns_line
        avg_str = row_text[row_text.find("avg ") + 4 : row_text.find(" per")]
        avg_turns = float(avg_str)

        # With 8 turns and 2 active games, average should be 4.0
        self.assertEqual(avg_turns, 4.0)

    def test_llm_response_turn_counting(self):
        """Test that each LLM response is counted as a turn, regardless of validity."""
        runner = BenchmarkRunner(self.config)

        with patch("src.benchmark.LLMPlayer") as mock_player:
            player_instance = mock_player.return_value

            # Simulate different LLM response scenarios
            player_instance.get_next_guess.side_effect = [
                None,  # Invalid format
                None,  # Another invalid format
                "1234",  # Valid guess but wrong
                None,  # Invalid format again
                "5678",  # Valid guess and correct
            ]

            # Mock game to return non-winning result for first valid guess,
            # then winning result for second valid guess
            game_responses = [(0, 0), (4, 0)]

            with patch.object(BullsAndCowsGame, "make_guess", side_effect=game_responses):
                with patch.object(BullsAndCowsGame, "get_target", return_value="5678"):
                    result = runner._run_single_game(self.config)

                    # Should count all LLM responses (5 total)
                    self.assertEqual(result["total_turns"], 5)
                    self.assertEqual(runner.progress.total_turns, 5)
                    self.assertEqual(result["format_failures"], 3)
                    self.assertTrue(result["success"])

    def test_format_failure_rate_calculation(self):
        """Test that format failure rate is calculated correctly in status table."""
        runner = BenchmarkRunner(self.config)

        # Simulate a mix of successful and failed attempts
        runner.progress.total_turns = 20  # Total LLM responses
        runner.progress.format_failures = 8  # Failed format attempts
        runner.progress.completed_games = 2
        runner.progress.successful_games = 1

        # Get the status table and render it to string
        table = runner._generate_status()
        console = Console(file=io.StringIO(), force_terminal=True)
        console.print(table)
        output = console.file.getvalue()

        # Find the line containing "Format Failures"
        failure_line = None
        for line in output.split("\n"):
            if "Format Failures" in line:
                failure_line = line
                break

        self.assertIsNotNone(failure_line, "Format Failures line not found in table")

        # Extract the failure rate from the string like "40.0% (8/20 turns)"
        row_text = failure_line
        end_idx = row_text.find("%")
        start_idx = end_idx - len("40.0")
        rate_str = row_text[start_idx:end_idx].strip()
        failure_rate = float(rate_str)

        # With 8 failures out of 20 turns, rate should be 40.0%
        self.assertEqual(failure_rate, 40.0)

    def test_concurrent_game_turn_counting(self):
        """Test turn counting when multiple games are running concurrently."""
        config = self.config.copy()
        config["benchmark"]["num_games"] = 3  # Run 3 games

        runner = BenchmarkRunner(config)

        with patch("src.benchmark.LLMPlayer") as mock_player:
            player_instance = mock_player.return_value

            # Each game will take 2 LLM responses
            player_instance.get_next_guess.side_effect = [
                None,
                "1234",  # Game 1
                None,
                "5678",  # Game 2
                None,
                "9012",  # Game 3
            ]

            # Mock game to return winning result for each valid guess
            with patch.object(BullsAndCowsGame, "make_guess", return_value=(4, 0)):
                with patch.object(
                    BullsAndCowsGame, "get_target", side_effect=["1234", "5678", "9012"]
                ):
                    metrics = runner.run_benchmark()

                    # Should have counted all LLM responses across all games
                    self.assertEqual(metrics["total_turns"], 6)  # 2 responses per game * 3 games
                    self.assertEqual(metrics["total_format_failures"], 3)  # 1 failure per game
                    self.assertEqual(metrics["success_rate"], 100.0)  # All games successful

    def test_max_turns_limit_with_format_failures(self):
        """Test that max turns limit considers LLM responses, not just valid guesses."""
        config = self.config.copy()
        config["benchmark"]["max_turns"] = 3  # Set very low max turns

        runner = BenchmarkRunner(config)

        with patch("src.benchmark.LLMPlayer") as mock_player:
            player_instance = mock_player.return_value

            # Simulate a mix of invalid and valid responses
            player_instance.get_next_guess.side_effect = [
                None,  # Invalid format (turn 1)
                "1234",  # Valid but wrong (turn 2)
                None,  # Invalid format (turn 3)
                "5678",  # Correct answer but it won't be retured
            ]

            with patch.object(BullsAndCowsGame, "make_guess", return_value=(0, 0)):
                with patch.object(BullsAndCowsGame, "get_target", return_value="5678"):
                    result = runner._run_single_game(config)

                    self.assertEqual(result["total_turns"], 3)
                    self.assertEqual(result["format_failures"], 2)
                    self.assertFalse(result["success"])
                    self.assertEqual(result["failure_reason"], "max_turns_exceeded")


if __name__ == "__main__":
    unittest.main()
