# `dzcb.data.dmrconfig`

The `.conf` files in this directory will be used to create
dmrconfig output files if no specific `--dmrconfig-template` is
specified.

## Format

dmrconfig template config files should NOT contain the analog, digital,
contacts, grouplists, scanlists, or zone table. Only the `Radio: `,
messages, ID, name, and intro screen fields (and any comments) are
allowed in the template.

## Directives

`dzcb` interprets lines containing `!dzcb.` in a special way.

This is not part of the dmrconfig format, these directives exist to give
some control over the output format.

### `!dzcb.ranges: M-N,O-P`

Remove channels with a frequency outside the given ranges M-N,O-P
but can be useful to reduce channel count and avoid uploading unsupported
channel data to your radio.

#### MD-UV380, UHF+VHF
```
# !dzcb.ranges: 136-174,400-480
```

#### MD-380 (UHF version)
```
# !dzcb.ranges: 400-480
```

#### Anytone D878UV (w/ 220)
```
# !dzcb.ranges: 136-174,222-225,400-480
```

### `!dzcb.include_docs: -`

If the value is `+`, then a comment is included describing the fields.

If the value is `-`, only the codeplug data is output

## Variables

The output generator will replace the following text in the template:

* `$DATE` - `%Y-%m-%d`
* `$ISODATE` - current timestamp ISO 8601 format
* `$TIME` - `%H:%M`
* `$SECTIME` - `%H:%M:%s`

## Supported Radios

The known valid radios are found in the `dzcb.output.dmrconfig` module:

* Anytone AT-D868UV
* Anytone AT-D878UV
* BTECH DMR-6x2
* Baofeng DM-1801
* Radioddity GD-77
* TYT MD-380
* TYT MD-390
* Zastone D900
* Zastone DP880
* Radtel RT-27D
* Baofeng RD-5R
* TYT MD-UV380
* TYT MD-UV390
* TYT MD-2017
* TYT MD-9600
* Retevis RT84