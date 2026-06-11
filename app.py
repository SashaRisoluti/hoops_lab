"""Local convenience launcher for the dashboard.

NOT used on HuggingFace Spaces: with `sdk: streamlit` the Space runs
`streamlit run` itself on the README's `app_file` (dashboard/app.py).
Running through `python -m streamlit` keeps the repo root on sys.path so
the `hoops_lab` package is importable.
"""

import subprocess
import sys

subprocess.run(
    [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "dashboard/app.py",
        "--server.port",
        "7860",  # HF Spaces standard port
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
    ],
    check=True,
)
