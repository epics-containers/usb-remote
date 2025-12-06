"""Utility functions for subprocess operations."""

import subprocess


def run_command(
    command: list[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a command using subprocess.run with common defaults.

    Args:
        command: The command and its arguments as a list of strings
        capture_output: Whether to capture stdout and stderr
        text: Whether to return output as text (string) instead of bytes
        check: Whether to raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess instance containing the result

    Raises:
        CalledProcessError: If check=True and the command returns non-zero
    """
    try:
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
        )
    except subprocess.CalledProcessError as e:
        print(f"\nCommand '{' '.join(command)}' failed with exit code {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise RuntimeError(e.stderr) from e
