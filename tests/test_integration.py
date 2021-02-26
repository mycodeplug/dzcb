"""
Integration tests combine multiple features
"""
from filecmp import dircmp
import os
from pathlib import Path
import subprocess
import shutil
import sys



def test_default_codeplug(tmp_path):
    output_dir = tmp_path / "default"
    output_dir.mkdir()
    cache_dir = output_dir / "cache"
    input_dir = Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "cache"
    shutil.copytree(input_dir, cache_dir)
    proc = subprocess.run(
        [
            sys.executable, "-m", "dzcb",
            "--scanlists-json", str(input_dir / "scanlists.json"),
            "--replacements", str(input_dir / "replacements.csv"),
            "--order", str(input_dir / "order.csv"),
            "--",
            str(output_dir),
        ],
        check=True,
    )
    for f in output_dir.glob("*.log"):
        f.rename(tmp_path / f.name)
    dircmp(input_dir, output_dir)

