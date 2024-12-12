# Bulls and Cows Benchmark Results

| Run ID | Model | Games | Success Rate | Avg Turns (success only) | Format Failures |
|--------|--------|-------|--------------|------------------------|----------------|
| benchmark_o1mini-4d | openai/o1-mini-2024-09-12 | 25 | 60.0% (40.7% - 76.6%) | 9.1 ± 2.7 | 23.1% |
| benchmark_sonnet35new-4d | openrouter/anthropic/claude-3.5-sonnet | 50 | 36.0% (24.1% - 49.9%) | 9.8 ± 4.0 | 0.0% |
| benchmark_4o-4d | openai/gpt-4o-2024-08-06 | 50 | 30.0% (19.1% - 43.8%) | 9.5 ± 3.6 | 0.0% |
| benchmark_4o-500-4d | azure/gpt-4o | 500 | 26.2% (22.5% - 30.2%) | 10.2 ± 3.4 | 0.4% |
| benchmark_4o-mini-4d | openai/gpt-4o-mini-2024-07-18 | 50 | 26.0% (15.9% - 39.6%) | 10.0 ± 3.1 | 0.1% |
| benchmark_dschat25-4d | openrouter/deepseek/deepseek-chat | 50 | 18.0% (9.8% - 30.8%) | 11.6 ± 3.6 | 3.3% |
| benchmark_qwq-pr-4d | openrouter/qwen/qwq-32b-preview | 50 | 14.0% (7.0% - 26.2%) | 8.1 ± 3.0 | 22.2% |
| benchmark_flash-20-exp-4d | gemini/gemini-2.0-flash-exp | 50 | 10.0% (4.3% - 21.4%) | 10.0 ± 2.7 | 0.0% |
| benchmark_geminipro15-002-4d | openrouter/google/gemini-pro-1.5 | 50 | 8.0% (3.2% - 18.8%) | 8.0 ± 4.1 | 0.1% |
| benchmark_llama31-405bi-4d | openrouter/meta-llama/llama-3.1-405b-instruct | 50 | 8.0% (3.2% - 18.8%) | 9.5 ± 3.3 | 3.0% |
| benchmark_flash15-002-4d | openrouter/google/gemini-flash-1.5 | 50 | 2.0% (0.4% - 10.5%) | 8.0 ± 0.0 | 0.9% |
| benchmark_haiku35-4d | anthropic/claude-3-5-haiku-20241022 | 50 | 0.0% (0.0% - 7.1%) | 0.0 ± 0.0 | 0.9% |
