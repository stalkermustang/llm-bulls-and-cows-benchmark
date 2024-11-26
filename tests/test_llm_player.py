import unittest
from unittest.mock import patch

import pytest

from src.game import BullsAndCowsGame
from src.llm_player import LLMPlayer
from src.prompts import (
    FIRST_TURN_MESSAGE,
    GUESS_PREFIX,
    NEXT_TURN_MESSAGE,
    REPEATING_DIGITS_ALLOWED,
    REPEATING_DIGITS_NOT_ALLOWED,
    RESULT_TEMPLATE,
    SYSTEM_PROMPT,
)


class TestLLMPlayer(unittest.TestCase):
    def setUp(self):
        self.config = {
            "benchmark": {
                "allow_repeating_digits": False,
                "max_turns": 10,
            },
            "llm": {
                "model": "test-model",
            },
        }
        self.player = LLMPlayer(self.config)
        self.game = BullsAndCowsGame(length=4, allow_repeating=False)

    def test_extract_and_validate_guess_valid(self):
        """Test extracting valid guesses from LLM responses."""
        # Simple case - just the guess
        content = f"{GUESS_PREFIX} 1234"
        self.assertEqual(self.player._extract_and_validate_guess(content, 4), "1234")

        # With explanation before the guess
        content = f"I think the number might be 1234 because...\n{GUESS_PREFIX} 1234"
        self.assertEqual(self.player._extract_and_validate_guess(content, 4), "1234")

        # Without space
        content = f"I think the number might be 1234 because...\n{GUESS_PREFIX}1234"
        self.assertEqual(self.player._extract_and_validate_guess(content, 4), "1234")

    @pytest.mark.filterwarnings("ignore::UserWarning")  # because of the last assert
    def test_extract_and_validate_guess_invalid(self):
        """Test handling of invalid guess formats."""
        test_cases = [
            f"{GUESS_PREFIX} 123",  # Too short
            f"{GUESS_PREFIX} 12345",  # Too long
            f"{GUESS_PREFIX} abcd",  # Non-digits
            "1234",  # No prefix
            "GUESS 1234",  # Wrong prefix
            "",  # Empty string
        ]

        for content in test_cases:
            self.assertIsNone(
                self.player._extract_and_validate_guess(content, 4),
                f"Should return None for invalid content: {content}",
            )

        # With content after the guess
        content = f"Let me try...\n{GUESS_PREFIX} 1234\nI hope this works!"
        self.assertIsNone(self.player._extract_and_validate_guess(content, 4))

    def test_first_turn_message_construction(self):
        """Test the construction of the first turn message."""
        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value.choices = [
                type("Choice", (), {"message": type("Message", (), {"content": "test"})})()
            ]

            self.player.get_next_guess(self.game, [])

            # Check that the system message and first turn message are correct
            messages = self.player.messages
            self.assertEqual(len(messages), 3)  # System + user + assistant
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[1]["role"], "user")
            self.assertEqual(messages[1]["content"], FIRST_TURN_MESSAGE)

            # Verify system message content
            system_content = messages[0]["content"]
            self.assertIn(REPEATING_DIGITS_NOT_ALLOWED, system_content)  # Correct rule

    def test_subsequent_turn_message_construction(self):
        """Test the construction of messages after the first turn."""
        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value.choices = [
                type("Choice", (), {"message": type("Message", (), {"content": "test"})})()
            ]

            # First turn to initialize
            self.player.get_next_guess(self.game, [])

            # Second turn with a previous guess result
            history = [("1234", (2, 1))]  # 2 bulls, 1 cow
            self.player.get_next_guess(self.game, history)

            # Check the latest message
            last_message = self.player.messages[-2]  # -1 is assistant's response
            self.assertEqual(last_message["role"], "user")
            expected_content = f"{RESULT_TEMPLATE.format(bulls=2, cows=1)} {NEXT_TURN_MESSAGE}"
            self.assertEqual(last_message["content"], expected_content)

    def test_repeating_digits_rule_in_system_prompt(self):
        """Test that the correct repeating digits rule is used in system prompt."""
        # Test with repeating digits allowed
        config_with_repeats = self.config.copy()
        config_with_repeats["benchmark"]["allow_repeating_digits"] = True
        player_with_repeats = LLMPlayer(config_with_repeats)

        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value.choices = [
                type("Choice", (), {"message": type("Message", (), {"content": "test"})})()
            ]

            player_with_repeats.get_next_guess(self.game, [])
            system_message = player_with_repeats.messages[0]["content"]
            self.assertIn(REPEATING_DIGITS_ALLOWED, system_message)

        # Test with repeating digits not allowed
        config_no_repeats = self.config.copy()
        config_no_repeats["benchmark"]["allow_repeating_digits"] = False
        player_no_repeats = LLMPlayer(config_no_repeats)

        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value.choices = [
                type("Choice", (), {"message": type("Message", (), {"content": "test"})})()
            ]

            player_no_repeats.get_next_guess(self.game, [])
            system_message = player_no_repeats.messages[0]["content"]
            self.assertIn(REPEATING_DIGITS_NOT_ALLOWED, system_message)


if __name__ == "__main__":
    unittest.main()
