"""Minimal stand-in for Forge's modules.errors."""

import sys
import traceback

reported = []


def report(message: str, *, exc_info: bool = False) -> None:
    reported.append(message)
    for line in message.splitlines():
        print("***", line, file=sys.stderr)
    if exc_info:
        print(traceback.format_exc(), file=sys.stderr)


def display(e, task, *, full_traceback=False):
    report(f"{task}: {e}")
