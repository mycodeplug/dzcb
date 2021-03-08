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

import dzcb.recipe


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
        Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "input"
    )
    input_cache_dir = (
        Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "cache"
    )
    shutil.copytree(input_cache_dir, cache_dir)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "dzcb",
            "--scanlists-json",
            str(input_dir / "scanlists.json"),
            "--replacements",
            str(input_dir / "replacements.csv"),
            "--order",
            str(input_dir / "order.csv"),
            "--anytone",
            "--farnsworth-template-json",
            str(input_dir / "md-uv380.json"),
            str(input_dir / "md-uv390.json"),
            "--dmrconfig-template",
            str(input_dir / "d878uv-int.conf"),
            str(input_dir / "md380-int.conf"),
            str(input_dir / "md-uv380-int.conf"),
            "--gb3gf",
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


def test_default_recipe(tmp_path):
    output_dir = tmp_path / "default"
    output_dir.mkdir()
    cache_dir = output_dir / "cache"
    input_dir = (
        Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "input"
    )
    input_cache_dir = (
        Path(os.path.dirname(__file__)) / "default-codeplug-expect-output" / "cache"
    )
    shutil.copytree(input_cache_dir, cache_dir)
    recipe = dzcb.recipe.CodeplugRecipe(
        scanlists_json=input_dir / "scanlists.json",
        order=input_dir / "order.csv",
        replacements=input_dir / "replacements.csv",
        output_anytone=True,
        output_dmrconfig=[
            input_dir / "d878uv-int.conf",
            input_dir / "md380-int.conf",
            input_dir / "md-uv380-int.conf",
        ],
        output_farnsworth=[
            input_dir / "md-uv380.json",
            input_dir / "md-uv390.json",
        ],
        output_gb3gf=True,
    )
    recipe.generate(output_dir)

    for f in output_dir.glob("*.log"):
        f.rename(tmp_path / f.name)
    dcmp = dircmp(input_dir.parent, output_dir, ignore=[".DS_Store"])
    diff_files = get_diff_files(dcmp, top_level=True)
    assert not diff_files
