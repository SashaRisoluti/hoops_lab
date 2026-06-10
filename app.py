"""HuggingFace Spaces entry point — thin wrapper that launches the dashboard.

HF Spaces requires an `app.py` at the repository root; the real Streamlit
application lives in `dashboard/app.py`. Running through `python -m streamlit`
keeps the repo root on sys.path so the `hoops_lab` package is importable.
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
