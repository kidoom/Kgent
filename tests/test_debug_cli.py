import os
import subprocess
import sys


def test_debug_cli_one_shot_calculator() -> None:
    env = os.environ.copy()
    env["KGENT_PROVIDER"] = "heuristic"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.debug_cli",
            "--provider",
            "heuristic",
            "--once",
            "帮我算一下 12 * 8 + 6",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )

    assert result.returncode == 0
    assert "CHECKPOINT" in result.stdout
    assert "messages (len=" in result.stdout
    assert "[call]" in result.stdout
    assert "[observe]" in result.stdout
    assert "calculator" in result.stdout
    assert "102" in result.stdout
