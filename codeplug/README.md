The codeplug directory contains directories that will be built into
codeplug import files by the CI process.

See default and default-tyt-md380 for more info. See kf7hvm for a customized codeplug.

Each directory should contain, at-minimum a `generate.sh` which will be called
by the workflow to create the codeplug.

The output top-level dir may be specified by the OUTPUT environment variable.
