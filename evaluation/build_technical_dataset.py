

"""
Builds a LangSmith evaluation dataset for technical_agent, and runs an
evaluation of technical_agent's actual scoring against the ground-truth
expected ranges.

Each example encodes a specific combination of technical indicators
(RSI, MACD, EMA20/50, price vs previous close) designed so that every
rule in technical_agent's prompt points consistently toward a known
expected outcome.

Note: price/indicator values are synthetic, chosen only to create
specific technical relationships — not tied to any real ticker's
actual historical data.

Run this occasionally (not part of the live application) — e.g. after
changing the prompt or switching models — to check for regressions.
"""

from langsmith import Client
from agents.technical_agent import score_technical_data
import os
from dotenv import load_dotenv
load_dotenv()

client = Client(api_key=os.environ.get("LANGSMITH_API_KEY"))

DATASET_NAME = "technical-agent-eval"

examples = [
    {
        "inputs": {
            "rsi": 25, "macd": 2.5, "ema20": 180, "ema50": 170,
            "current_price": 185, "previous_close": 180, "percent_change": 2.8
        },
        "outputs": {"expected_range": "bullish", "expected_score_min": 75, "expected_score_max": 100}
    },
    {
        "inputs": {
            "rsi": 82, "macd": -2.2, "ema20": 155, "ema50": 165,
            "current_price": 150, "previous_close": 153, "percent_change": -2.0
        },
        "outputs": {"expected_range": "bearish", "expected_score_min": 0, "expected_score_max": 25}
    },
    {
        "inputs": {
            "rsi": 50, "macd": 0.1, "ema20": 160, "ema50": 159,
            "current_price": 160.5, "previous_close": 160, "percent_change": 0.3
        },
        "outputs": {"expected_range": "neutral", "expected_score_min": 40, "expected_score_max": 60}
    },
    {
        "inputs": {
            "rsi": 25, "macd": -1.8, "ema20": 145, "ema50": 155,
            "current_price": 144, "previous_close": 146, "percent_change": -1.4
        },
        "outputs": {"expected_range": "mixed-leaning-bearish", "expected_score_min": 30, "expected_score_max": 55}
    },
    {
        "inputs": {
            "rsi": 75, "macd": 3.0, "ema20": 190, "ema50": 175,
            "current_price": 195, "previous_close": 188, "percent_change": 3.7
        },
        "outputs": {"expected_range": "mixed-leaning-bullish", "expected_score_min": 60, "expected_score_max": 85}
    },
]


def build_dataset():
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Ground-truth technical indicator scenarios for evaluating technical_agent's scoring logic"
    )
    for i, ex in enumerate(examples, start=1):
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            dataset_id=dataset.id
        )
        print(f"Added example {i}: {ex['outputs']['expected_range']}")
    print(f"\nDataset '{DATASET_NAME}' created with {len(examples)} examples.")


def run_evaluation():
    dataset_examples = client.list_examples(dataset_name=DATASET_NAME)

    results = []
    for example in dataset_examples:
        inputs = example.inputs
        fake_quote = {
            "current_price": inputs["current_price"],
            "change": inputs["current_price"] - inputs["previous_close"],
            "percent_change": inputs["percent_change"],
            "high": inputs["current_price"] + 1,
            "low": inputs["current_price"] - 1,
            "previous_close": inputs["previous_close"]
        }
        fake_indicators = {
            "rsi": inputs["rsi"],
            "macd": inputs["macd"],
            "ema20": inputs["ema20"],
            "ema50": inputs["ema50"]
        }

        result = score_technical_data("EVAL_TEST", fake_quote, fake_indicators)
        actual_score = result["technical_score"] 

        expected_min = example.outputs["expected_score_min"]
        expected_max = example.outputs["expected_score_max"]
        expected_range = example.outputs["expected_range"]

        passed = expected_min <= actual_score <= expected_max

        results.append(passed)

        status = "PASS" if passed else "FAIL"
        print(f"{status} | {expected_range:25s} | actual={actual_score:.1f} | expected=[{expected_min}, {expected_max}]")

    print(f"\n{sum(results)}/{len(results)} scenarios passed")


if __name__ == "__main__":
    # build_dataset()  # only run once, to (re)create the dataset — commented out so re-running this file evaluates instead
    run_evaluation()