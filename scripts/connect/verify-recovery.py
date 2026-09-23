#!/usr/bin/env python3
"""Compile and run the Unreal-independent pending-identity codec tests."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/connect/transaction-recovery-test.cpp"
INCLUDE = ROOT / "Source/SoraArena/Private"
SUBSYSTEM = INCLUDE / "ArenaWalletSubsystem.cpp"


def check_submission_order() -> None:
    source = SUBSYSTEM.read_text(encoding="utf-8")
    submit = source.split("bool UArenaWalletSubsystem::SubmitSignedTestTransaction()", 1)[1].split(
        "bool UArenaWalletSubsystem::ReconcileTransaction()", 1
    )[0]
    restore = source.split("void UArenaWalletSubsystem::RestorePendingTransactionIdentity()", 1)[1].split(
        "bool UArenaWalletSubsystem::IsRecoveryIdentityCurrent()", 1
    )[0]
    status = source.split("void UArenaWalletSubsystem::PollTransactionStatus()", 1)[1].split(
        "void UArenaWalletSubsystem::CancelTransactionRequest()", 1
    )[0]
    assert submit.index("PersistRecovery(IdentityRecord") < submit.index("SetURL(SubmissionOrigin")
    assert submit.index("PersistRecovery(IdentityRecord") < submit.index("ProcessRequest()")
    assert submit.index("Erase(LastSignedTransactionBase64)") < submit.index("ProcessRequest()")
    assert "ProcessRequest()" not in restore and "LastSignedTransactionBase64 =" not in restore
    assert "IsRecoveryIdentityCurrent()" in status
    assert "ForgetRecovery(Current" in status


def main() -> int:
    check_submission_order()
    environment = os.environ.copy()
    arguments: list[str] = []
    if sys.platform == "darwin":
        local_xcode = Path.home() / "Applications/SORAToolchain/Xcode_26.1.1.app/Contents/Developer"
        if local_xcode.is_dir():
            environment["DEVELOPER_DIR"] = str(local_xcode)
        sdk = subprocess.check_output(
            ["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=environment, text=True
        ).strip()
        compiler = subprocess.check_output(
            ["xcrun", "--sdk", "macosx", "--find", "clang++"], env=environment, text=True
        ).strip()
        arguments = ["-isysroot", sdk]
    else:
        compiler = shutil.which("clang++") or shutil.which("g++")
        if not compiler:
            raise SystemExit("C++17 compiler not found")
    with tempfile.TemporaryDirectory(prefix="sora-recovery-") as scratch:
        binary = Path(scratch) / "transaction-recovery-test"
        command = [
            compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
            *arguments, "-I", str(INCLUDE), str(SOURCE), "-o", str(binary),
        ]
        subprocess.run(command, check=True, env=environment)
        subprocess.run([str(binary)], check=True, env=environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
