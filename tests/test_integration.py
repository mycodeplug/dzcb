"""
Integration tests combine multiple features
"""
import difflib
from filecmp import dircmp
import os
from pathlib import Path
import subprocess
import shutil
import sys


def get_diff_files(dcmp, top_level=False):
    msg = []
    for name in dcmp.diff_files:
        l, r = Path(dcmp.left) / name, Path(dcmp.right) / name
        diff = tuple(
            difflib.unified_diff(
                l.read_text().splitlines(),
                r.read_text().splitlines(),
                fromfile=str(l),
                tofile=str(r),
                lineterm="",
            )
        )
        if diff:
            print("\n".join(diff))
            msg.append(f"diff in: {l.parts[-3:]}")
    if dcmp.left_only:
        msg.append(f"left only: {dcmp.left_only}")
    if dcmp.right_only:
        msg.append(f"right only: {dcmp.right_only}")
    for sub_dcmp in dcmp.subdirs.values():
        msg.extend(get_diff_files(sub_dcmp))
    if top_level:
        print("\n".join(msg))
    return msg


def test_default_codeplug(tmp_path):
    output_dir = tmp_path / "default"
    output_dir.mkdir()
    cache_dir = output_dir / "cache"
    input_dir = (
        Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "cache"
    )
    shutil.copytree(input_dir, cache_dir)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "dzcb",
            "--farnsworth-template-json",
            str(input_dir / ".." / "editcp" / "md-uv380.json"),
            str(input_dir / ".." / "editcp" / "md-uv390.json"),
            "--scanlists-json",
            str(input_dir / "scanlists.json"),
            "--replacements",
            str(input_dir / "replacements.csv"),
            "--order",
            str(input_dir / "order.csv"),
            "--",
            str(output_dir),
        ],
        check=True,
    )
    for f in output_dir.glob("*.log"):
        f.rename(tmp_path / f.name)
    dcmp = dircmp(input_dir.parent, output_dir, ignore=[".DS_Store"])
    diff_files = get_diff_files(dcmp, top_level=True)
    assert not diff_files
