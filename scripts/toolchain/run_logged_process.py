#!/usr/bin/env python3
"""Retain a command's raw output until its inherited stdout/stderr reaches EOF."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

COLLECTION_FAILED = 125


def shell_status(returncode: int) -> int:
    return returncode if returncode >= 0 else 128 - returncode


def run(command: list[str], log: Path, drain_timeout: float) -> dict:
    """Only this process writes the log; descendants inherit the pipe, not it.

    The deadline starts when the launched process exits, not while it is doing
    work. EOF is the completion condition, never a quiet interval. No descendant
    is looked up or signalled, including an already running trace server.
    """
    if not command or not math.isfinite(drain_timeout) or drain_timeout <= 0:
        raise ValueError("command and finite positive drain timeout are required")
    result = {"process_returncode": None, "runner_status": COLLECTION_FAILED,
              "stream_eof": False, "drain_timeout_seconds": drain_timeout,
              "failure": None}
    digest = hashlib.sha256()
    size = 0
    with log.open("xb") as output:
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError as error:
            result["failure"] = f"could not launch process: {error}"
        else:
            # Use unbuffered fd reads so every byte (including non-UTF8) survives.
            # The file descriptor for output is non-inheritable and close_fds is
            # true, so only this collector can append to the archived log.
            with process.stdout, selectors.DefaultSelector() as events:
                events.register(process.stdout, selectors.EVENT_READ)
                deadline = None
                while True:
                    code = process.poll()
                    if code is not None and deadline is None:
                        result["process_returncode"] = code
                        deadline = time.monotonic() + drain_timeout
                    remaining = None if deadline is None else deadline - time.monotonic()
                    if remaining is not None and remaining <= 0:
                        result["failure"] = (
                            f"inherited log stream did not reach EOF within {drain_timeout:g}s "
                            f"after process exit ({code}); capture log is incomplete")
                        break
                    # Periodically observe process exit even when a descendant
                    # holds the pipe open without writing; select still wakes
                    # immediately for output/EOF, with no settling sleep.
                    if not events.select(0.1 if remaining is None else min(0.1, remaining)):
                        continue
                    data = os.read(process.stdout.fileno(), 65536)
                    if not data:
                        result["stream_eof"] = True
                        break
                    output.write(data)
                    output.flush()
                    digest.update(data)
                    size += len(data)
            # EOF may precede process exit (a command can close its stdio).
            # Preserve the original wait semantics in that case.
            result["process_returncode"] = process.wait()
            if result["failure"] is None:
                result["runner_status"] = shell_status(result["process_returncode"])
    result.update(log_bytes=size, log_sha256=digest.hexdigest())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--drain-timeout", type=float, default=60.0,
                        help="maximum post-process seconds to await stream EOF (default: 60)")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = run(command, args.log, args.drain_timeout)
        with args.receipt.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
    except (OSError, ValueError) as error:
        print(f"FAIL: capture log collection: {error}", file=sys.stderr)
        return COLLECTION_FAILED
    if result["failure"]:
        print(f"FAIL: capture log collection: {result['failure']}", file=sys.stderr)
    return result["runner_status"]


if __name__ == "__main__":
    raise SystemExit(main())
