#!/usr/bin/env python3

# This script generates the same codeplug as generate.sh
# by running dzcb via the python API

from importlib_resources import files
from pathlib import Path
import os

import dzcb.data
from dzcb.recipe import CodeplugRecipe

cp_dir = Path(__file__).parent
output = Path(os.environ.get("OUTPUT") or (cp_dir / ".." / ".." / "OUTPUT"))

CodeplugRecipe(
    source_pnwdigital=True,
    source_seattledmr=True,
    source_default_k7abd=True,
    source_repeaterbook_proximity=files(dzcb.data) / "repeaterbook_proximity_zones.csv",
    repeaterbook_states=["washington", "oregon"],
    repeaterbook_name_format="{Nearest City} {Frequency}",
    scanlists_json=cp_dir / "scanlists.json",
    replacements=cp_dir / "replacements.csv",
    order=cp_dir / "order.csv",
    output_anytone=True,
    output_dmrconfig=True,
    output_farnsworth=True,
    output_gb3gf=True
).generate(output / cp_dir.name)
