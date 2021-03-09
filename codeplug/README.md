The codeplug directory contains directories that will be built into
codeplug import files by the CI process.

See default and default-tyt-md380 for more info.

Each directory should contain, at-minimum a `generate.py` or `generate.sh` script
which will be called by the workflow to create the codeplug(s).

The output top-level dir may be specified by the OUTPUT environment variable.
