#!/usr/bin/env python3

# execute all generate.py files in subdirectories of this
# scripts directory

from pathlib import Path
import subprocess
import sys

cp_dir = Path(__file__).parent

for genpy in cp_dir.glob("**/generate.py"):
    subprocess.check_call([sys.executable, genpy])
