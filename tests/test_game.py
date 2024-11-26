import unittest
from unittest.mock import patch

from src.game import BullsAndCowsGame


class TestBullsAndCowsGame(unittest.TestCase):
    def setUp(self):
        # Create a game instance for each test
        self.game = BullsAndCowsGame(length=4, allow_repeating=False)

    def test_initialization(self):
        """Test game initialization with different parameters"""
        # Default parameters
        game = BullsAndCowsGame()
        self.assertEqual(len(game.get_target()), 4)
        self.assertEqual(len(set(game.get_target())), 4)  # All digits should be unique

        # Custom length
        game = BullsAndCowsGame(length=6)
        self.assertEqual(len(game.get_target()), 6)
        self.assertEqual(len(set(game.get_target())), 6)

        # Allow repeating digits
        game = BullsAndCowsGame(length=4, allow_repeating=True)
        self.assertEqual(len(game.get_target()), 4)
        # Note: We can't test for uniqueness here as digits might repeat

    def test_target_generation_no_repeats(self):
        """Test target number generation without repeating digits"""
        game = BullsAndCowsGame(length=4, allow_repeating=False)
        target = game.get_target()

        self.assertTrue(target.isdigit())
        self.assertEqual(len(target), 4)
        self.assertEqual(len(set(target)), 4)  # All digits should be unique

    def test_target_generation_with_repeats(self):
        """Test target number generation with repeating digits allowed"""
        game = BullsAndCowsGame(length=4, allow_repeating=True)
        target = game.get_target()

        self.assertTrue(target.isdigit())
        self.assertEqual(len(target), 4)
        # Note: We can't test for specific patterns as it's random

    def test_make_guess_exact_match(self):
        """Test making a guess that exactly matches the target"""
        target = self.game.get_target()
        bulls, cows = self.game.make_guess(target)

        self.assertEqual(bulls, 4)
        self.assertEqual(cows, 0)
        self.assertEqual(self.game.turns, 1)

    def test_make_guess_no_match(self):
        """Test making a guess with no matching digits"""
        # Mock the target to be "1234"
        with patch.object(self.game, "target", "1234"):
            bulls, cows = self.game.make_guess("5678")
            self.assertEqual(bulls, 0)
            self.assertEqual(cows, 0)

    def test_make_guess_all_cows(self):
        """Test making a guess where all digits are correct but in wrong positions"""
        # Mock the target to be "1234"
        with patch.object(self.game, "target", "1234"):
            bulls, cows = self.game.make_guess("4321")
            self.assertEqual(bulls, 0)
            self.assertEqual(cows, 4)

    def test_make_guess_mixed_result(self):
        """Test making a guess with both bulls and cows"""
        # Mock the target to be "1234"
        with patch.object(self.game, "target", "1234"):
            bulls, cows = self.game.make_guess("1432")  # 1 and 3 are bulls, 4 and 2 are cows
            self.assertEqual(bulls, 2)
            self.assertEqual(cows, 2)

    def test_make_guess_invalid_length(self):
        """Test making guesses with invalid lengths"""
        with self.assertRaises(ValueError):
            self.game.make_guess("123")  # Too short

        with self.assertRaises(ValueError):
            self.game.make_guess("12345")  # Too long

    def test_make_guess_invalid_input(self):
        """Test making guesses with invalid input"""
        invalid_inputs = [
            "abc1",  # Contains letters
            "1.23",  # Contains decimal point
            "12 3",  # Contains space
            "-123",  # Contains negative sign
            "12.34",  # Contains decimal point
            "123a",  # Contains letter at end
            "    ",  # All spaces
            "",  # Empty string
        ]

        for invalid_input in invalid_inputs:
            with self.assertRaises(ValueError, msg=f"Failed to raise for input: {invalid_input}"):
                self.game.make_guess(invalid_input)

    def test_make_guess_turn_counter(self):
        """Test that the turn counter increments correctly"""
        self.assertEqual(self.game.turns, 0)

        self.game.make_guess("1234")
        self.assertEqual(self.game.turns, 1)

        self.game.make_guess("5678")
        self.assertEqual(self.game.turns, 2)

    def test_is_won(self):
        """Test the is_won method"""
        self.assertTrue(self.game.is_won(4, 0))  # All bulls
        self.assertFalse(self.game.is_won(3, 1))  # 3 bulls, 1 cow
        self.assertFalse(self.game.is_won(0, 4))  # All cows
        self.assertFalse(self.game.is_won(0, 0))  # No matches

    def test_repeated_guesses(self):
        """Test making the same guess multiple times"""
        # Mock the target to be "1234"
        with patch.object(self.game, "target", "1234"):
            # Make the same guess multiple times
            for _ in range(3):
                bulls, cows = self.game.make_guess("5678")
                self.assertEqual(bulls, 0)
                self.assertEqual(cows, 0)

    def test_edge_cases(self):
        """Test edge cases"""
        # Test with all same digits when repeats are allowed
        game = BullsAndCowsGame(length=4, allow_repeating=True)
        with patch.object(game, "target", "1111"):
            bulls, cows = game.make_guess("1111")
            self.assertEqual(bulls, 4)
            self.assertEqual(cows, 0)

            bulls, cows = game.make_guess("2222")
            self.assertEqual(bulls, 0)
            self.assertEqual(cows, 0)

        # Test with sequential digits
        game_seq = BullsAndCowsGame(length=4, allow_repeating=False)
        with patch.object(game_seq, "target", "0123"):
            bulls, cows = game_seq.make_guess("3210")
            self.assertEqual(bulls, 0)
            self.assertEqual(cows, 4)

    def test_make_guess_with_leading_zeros(self):
        """Test making guesses with leading zeros"""
        # Mock the target to be "0123"
        with patch.object(self.game, "target", "0123"):
            # Valid guesses with leading zeros
            bulls, cows = self.game.make_guess("0123")
            self.assertEqual(bulls, 4)
            self.assertEqual(cows, 0)

            bulls, cows = self.game.make_guess("0321")  # 0 and 2 are bulls, 3 and 1 are cows
            self.assertEqual(bulls, 2)
            self.assertEqual(cows, 2)

    def test_maximum_length_game(self):
        """Test game with maximum possible length (10) when repeating is not allowed"""
        game = BullsAndCowsGame(length=10, allow_repeating=False)
        target = game.get_target()
        self.assertEqual(len(target), 10)
        self.assertEqual(len(set(target)), 10)  # All digits must be unique

        # Make a guess with all digits in wrong positions
        reversed_target = target[::-1]
        bulls, cows = game.make_guess(reversed_target)
        if target != reversed_target:  # Only check if target isn't palindromic
            self.assertEqual(bulls + cows, 10)

    def test_minimum_length_game(self):
        """Test game with minimum length (1)"""
        game = BullsAndCowsGame(length=1, allow_repeating=False)
        target = game.get_target()
        self.assertEqual(len(target), 1)
        self.assertTrue(target.isdigit())

        # Test all possible guesses
        for i in range(10):
            bulls, cows = game.make_guess(str(i))
            if str(i) == target:
                self.assertEqual(bulls, 1)
                self.assertEqual(cows, 0)
            else:
                self.assertEqual(bulls, 0)
                self.assertEqual(cows, 0)

    def test_repeated_digits_in_guess(self):
        """Test handling of repeated digits in guess when repeating is not allowed"""
        game = BullsAndCowsGame(length=4, allow_repeating=False)
        with patch.object(game, "target", "1234"):
            bulls, cows = game.make_guess("1111")
            self.assertEqual(bulls, 1)
            self.assertEqual(cows, 0)

    def test_repeated_digits_in_target(self):
        """Test handling of repeated digits in target when repeating is allowed"""
        game = BullsAndCowsGame(length=4, allow_repeating=True)
        with patch.object(game, "target", "1122"):
            bulls, cows = game.make_guess("1212")
            self.assertEqual(bulls, 2)
            self.assertEqual(cows, 2)

    def test_all_zeros(self):
        """Test handling of all zeros as guess"""
        game = BullsAndCowsGame(length=4, allow_repeating=True)
        with patch.object(game, "target", "0000"):
            bulls, cows = game.make_guess("0000")
            self.assertEqual(bulls, 4)
            self.assertEqual(cows, 0)


if __name__ == "__main__":
    unittest.main()
