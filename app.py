"""Local convenience launcher for the dashboard.

NOT the entry point of any deployment. Streamlit Community Cloud runs
`streamlit run` itself against `dashboard/app.py`; pointing a host at this
file would spawn a nested server the host never sees.

Running through `python -m streamlit` keeps the repo root on sys.path so the
`hoops_lab` package is importable.
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
        "8501",  # Streamlit's default
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
    ],
    check=True,
)
