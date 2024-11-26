import random
from typing import List, Tuple


class BullsAndCowsGame:
    def __init__(self, length: int = 4, allow_repeating: bool = False):
        self.length = length
        self.allow_repeating = allow_repeating
        self.target = self._generate_number()
        self.turns = 0

    def _generate_number(self) -> str:
        if self.allow_repeating:
            return "".join(str(random.randint(0, 9)) for _ in range(self.length))
        else:
            digits = list(range(10))
            random.shuffle(digits)
            return "".join(map(str, digits[: self.length]))

    def make_guess(self, guess: str) -> Tuple[int, int]:
        """Returns (bulls, cows) for the guess."""
        if len(guess) != self.length or not guess.isdigit():
            raise ValueError(f"Invalid guess: {guess}. Must be {self.length} digits.")

        # First pass: count bulls and mark used positions
        bulls = 0
        used_target_positions = set()
        used_guess_positions = set()

        for i, (g, t) in enumerate(zip(guess, self.target)):
            if g == t:
                bulls += 1
                used_target_positions.add(i)
                used_guess_positions.add(i)

        # Second pass: count cows
        cows = 0
        # For each unused position in guess
        for i in range(self.length):
            if i in used_guess_positions:
                continue
            g = guess[i]
            # Look for this digit in unused target positions
            for j in range(self.length):
                if j in used_target_positions:
                    continue
                if g == self.target[j]:
                    cows += 1
                    used_target_positions.add(j)
                    break

        self.turns += 1
        return bulls, cows

    def is_won(self, bulls: int, cows: int) -> bool:
        return bulls == self.length

    def get_target(self) -> str:
        return self.target
