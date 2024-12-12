import warnings
from typing import Dict, List, Optional, Tuple

import litellm
from litellm import Router

from .game import BullsAndCowsGame
from .prompts import (
    FIRST_TURN_MESSAGE,
    FORMAT_ERROR_MESSAGE,
    GUESS_PREFIX,
    NEXT_TURN_MESSAGE,
    REPEATING_DIGITS_ALLOWED,
    REPEATING_DIGITS_NOT_ALLOWED,
    RESULT_TEMPLATE,
    SYSTEM_PROMPT,
)


class LLMPlayer:
    def __init__(self, config: Dict):
        self.config = config
        self.messages = []

        # Set litellm parameters
        litellm.set_verbose = self.config["llm"].get("litellm_verbose", False)
        litellm.drop_params = True

        model_list = [
            {
                "model_name": self.config["llm"]["model"],
                "litellm_params": {"model": self.config["llm"]["model"]},
            }
        ]

        self.router = Router(  # used for handling Timeouts (mostly, free tier Gemini)
            model_list, cooldown_time=45, allowed_fails=1, num_retries=3, retry_after=50  # seconds
        )

    def get_next_guess(
        self,
        game: BullsAndCowsGame,
        history: List[Tuple[str, Tuple[int, int]]],
        last_error: Optional[str] = None,
    ) -> Optional[str]:
        # Initialize messages list if this is the first turn
        if not self.messages:
            repeat_rule = (
                REPEATING_DIGITS_ALLOWED
                if self.config["benchmark"]["allow_repeating_digits"]
                else REPEATING_DIGITS_NOT_ALLOWED
            )
            self.messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(length=game.length, repeat_rule=repeat_rule),
                }
            ]
            self.messages.append({"role": "user", "content": FIRST_TURN_MESSAGE})
        else:
            # Add the result of the previous guess and/or error feedback
            content_parts = []
            if last_error:
                content_parts.append(FORMAT_ERROR_MESSAGE.format(length=game.length))
            elif history:
                last_guess, (bulls, cows) = history[-1]
                content_parts.append(RESULT_TEMPLATE.format(bulls=bulls, cows=cows))
            else:
                raise ValueError("Unexpected behaviour.")

            content_parts.append(NEXT_TURN_MESSAGE)
            self.messages.append({"role": "user", "content": " ".join(content_parts)})

        # Get model's response
        try:
            # Only model is required
            if "model" not in self.config["llm"]:
                raise ValueError("LLM model must be specified in config")

            # Build completion parameters, passing through all config values
            completion_params = {
                "model": self.config["llm"]["model"],
                "messages": self.messages,
                # retries are controlled via Router now
                # "retry_strategy": "exponential_backoff_retry",
            }

            # Add optional parameters if they exist in config, e.g., temperature or max tokens
            for param in self.config["llm"]:
                if param not in completion_params and not param.startswith("litellm"):
                    completion_params[param] = self.config["llm"][param]

            response = self.router.completion(**completion_params)

            content = response.choices[0].message.content
            # Add model's response to history
            self.messages.append({"role": "assistant", "content": content})

        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return None

        # Extract guess
        guess = self._extract_and_validate_guess(content, game.length)

        return guess

    @staticmethod
    def _extract_and_validate_guess(content: str, guess_len: int) -> Optional[str]:
        content_rows = content.strip().split("\n")
        for idx, line in enumerate(content_rows):
            if line.startswith(GUESS_PREFIX):
                # only the last row
                if idx == len(content_rows) - 1:
                    guess = line.split(":")[1].strip()
                    if len(guess) == guess_len and guess.isdigit():
                        return guess
                else:
                    warnings.warn(
                        f"{GUESS_PREFIX} was parsed not from the last row. Skipping...", UserWarning
                    )
        return None

    def get_conversation_state(self) -> Dict:
        """Return the current conversation state with the LLM."""
        return {"messages": self.messages}
