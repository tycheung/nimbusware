"""Demo application module for token budget golden fixtures."""

HELPER_LINES = [f"def helper_{i}() -> int:\n    return {i}\n" for i in range(120)]


def main() -> str:
    return "app"


def run() -> None:
    for fn in HELPER_LINES:
        _ = fn
    print(main())
