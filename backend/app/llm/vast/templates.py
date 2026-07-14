DRY_RUN_TEST_RESPONSE = (
    "Dry-run Vast.ai model response. No GPU was rented, no external model was called, "
    "and this output is for connectivity testing only."
)


def build_test_prompt(prompt: str) -> str:
    return (
        "Respond in an educational, non-advisory tone. Do not provide buy/sell "
        "instructions, wallet actions, or trade execution guidance.\n\n"
        f"Prompt: {prompt}"
    )
