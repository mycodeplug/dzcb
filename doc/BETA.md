# `dzcb` 0.3 Public Beta

Thank you for your interest in beta testing [`dzcb`](https://github.com/mycodeplug/dzcb).
Please remember that this project is developed by a single person in spare time only.

See [HISTORY](./HISTORY.md) for motivation, criticisms, and feature development
backstory.

## Scope of Current Testing

I have personally tested dzcb with the following radios:

  * TYT MD-UV380 (editcp JSON and dmrconfig)
  * Anytone D878UV (CSV and dmrconfig)
  * Radioddity GD-77 (Stock firmware and dmrconfig)

I test the pnwdigital, seattledmr, custom k7abd, and repeaterbook sources.

Additionally, I have tested the exclude, order, and replacements CSV modifications
as well as custom scanlists.

## Testing Needed

Testing is needed for the following popular radios:
   
  * Anytone 578
  * TYT MD380 - UHF or VHF only
  * BTECH DMR-6x2
  * Baofeng RD-5R

Testing is needed for the `include` CSV and repeaterbook name format.

**I would also like feedback on general usability and quality of documentation.**

## Where to Start

At least scan through the [`dzcb` README](/README.md) to get an idea
of what features are available and what formats are supported.

Look at
[`mycodeplug/example-codeplug`](https://github.com/mycodeplug/example-codeplug)
for a fully working example with sample CSV files and scripts to generate the
codeplug.

If you're brand new to codeplug generators and github, please see the
[WALKTHROUGH](/doc/WALKTHROUGH.md) for a step-by-step guide to building a
codeplug online using github actions.

If you already use K7ABD's `anytone-config-builder`, then you likely already have
files that will work with `dzcb`.

For example, to install dzcb and build existing ACB CSV files into dmrconfig codeplug
files (requires python 3.6+):

```
pip install dzcb~=0.3.1
python -m dzcb --k7abd /path/to/existing/acb_csv --dmrconfig -- /tmp/new-codeplug
```

## Known Issues

* Invalid CSV input may cause the program to exit without indicating which file was
  problematic. This will be fixed in a later release. See [issue #73](https://github.com/mycodeplug/dzcb/issues/73)

# Support

Unfortunately I'm not able to provide personalized support for connecting your
radio, installing drivers, python, or CPS software, or any general DMR questions.

## Feedback and Feature Requests

Please file an [issue](https://github.com/mycodeplug/dzcb/issues/new) or email
`kf7hvm@0x26.net` with any usability feedback or feature requests. Be sure to
include detailed descriptions, example usage, and sample files and command
lines that will help me understand the request.

## Bugs

If you have discovered a bug, please file an
[issue](https://github.com/mycodeplug/dzcb/issues/new) in this repository,
including the full codeplug output directory and log file, the full error
message, operating system and python version, and any other relevant details.
