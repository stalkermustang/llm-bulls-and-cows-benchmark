"""Module containing all prompt-related strings used in the Bulls and Cows game."""

# Core format identifiers
GUESS_PREFIX = "GUESS:"  # The prefix used to identify a guess in the model's response

# System prompt template for the LLM player
SYSTEM_PROMPT = f"""You are playing the Bulls and Cows number guessing game. The rules are:
1. There is a secret {{length}}-digit number you need to guess (using digits 0-9)
2. {{repeat_rule}}
3. After each guess, you'll receive:
   - Bulls: number of digits that are correct AND in the right position
   - Cows: number of digits that are correct BUT in the wrong position

You can explain your reasoning before making a guess.
Always end your response with a line starting with '{GUESS_PREFIX}' followed by your {{length}}-digit number.
DO NOT use any other formatting (e.g., Markdown or bold) in the last line of your response."""

# Messages for game interaction
FIRST_TURN_MESSAGE = "Let's start the game. Make your first guess:"
NEXT_TURN_MESSAGE = "Make your next guess:"
RESULT_TEMPLATE = "Your last guess resulted in: {bulls} bulls (correct position) and {cows} cows (wrong position)."

# Format validation
FORMAT_ERROR_MESSAGE = f"Failed to parse your guess from the last line of your response. It must start with '{GUESS_PREFIX}' followed by exactly {{length}} digits (0-9), and WITHOUT any other formatting (e.g., Markdown or bold)."

# Rules text
REPEATING_DIGITS_ALLOWED = "The same digit can appear multiple times in the number"
REPEATING_DIGITS_NOT_ALLOWED = "Each digit (0-9) can appear at most once in the number"
