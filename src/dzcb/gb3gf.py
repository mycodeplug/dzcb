"""
Write series of CSV files acceptable for import into gb3gf codeplug tool

Ex: OpenGD77
"""

def Codeplug_to_gb3gf_opengd77_csv(cp, output_dir):
    # Channels.csv, Contacts.csv, TG_List.csv, Zones.csv
    with open("{}/Contacts.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(
            f, ["Contact Name", "ID", "ID Type", "TS Override"], delimiter=";"
        )
        csvw.writeheader()
        for tg in cp.contacts:
            csvw.writerow(
                {
                    "Contact Name": tg.Name,
                    "ID": tg.CallID,
                    "ID Type": tg.CallType,
                    "TS Override": tg.timeslot.value,
                }
            )
    channel_fields = [
        "Channel Number",
        "Channel Name",
        "Channel Type",
        "Rx Frequency",
        "Tx Frequency",
        "Colour Code",
        "Timeslot",
        "Contact",
        "TG List",
        "RX Tone",
        "TX Tone",
        "Power",
        "Bandwidth",
        "Squelch",
        "Rx Only",
        "Zone Skip",
        "All Skip",
        "TOT",
        "VOX",
    ]
    with open("{}/Channels.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(f, channel_fields, delimiter=";")
        csvw.writeheader()
        for ix, channel in enumerate(cp.channels):
            csvw.writerow(
                {
                    "Channel Number": ix + 1,
                    "Channel Name": channel.Name,
                    "Channel Type": channel.ChannelMode,
                    "Rx Frequency": channel.RxFrequency,
                    "Tx Frequency": channel.RxFrequency + channel.TxFrequencyOffset,
                    "Colour Code": channel.ColorCode or "None",
                    "Timeslot": 1,
                    "Contact": channel.ContactName or "N/A",
                    "TG List": channel.GroupList or "None",
                    "RX Tone": channel.CtcssDecode or "None",
                    "TX Tone": channel.CtcssEncode or "None",
                    "Power": channel.Power,
                    "Bandwidth": str(channel.Bandwidth) + "KHz",
                    "Squelch": "Disabled",
                    "Rx Only": channel.value_replacements[channel.RxOnly],
                    "Zone Skip": "No",
                    "All Skip": "No",
                    "TOT": channel.Tot,
                    "VOX": channel.value_replacements[channel.Vox],
                }
            )
    tg_fields = ["TG List Name"] + ["Contact {}".format(x) for x in range(1, 33)]
    with open("{}/TG_Lists.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(f, tg_fields, delimiter=";")
        csvw.writeheader()
        for gl in cp.grouplists:
            tg_list = {"TG List Name": gl.Name}
            contacts = list(gl.Contact)
            remove_tgs = list(reversed(TALKGROUP_LIST_OVERFLOW))
            # remove some talkgroups to get under the limit
            while len(contacts) > 32:
                try:
                    contacts.remove(remove_tgs.pop())
                except ValueError:
                    pass
            for ix, tg in enumerate(contacts):
                tg_list["Contact {}".format(ix + 1)] = tg
            csvw.writerow(tg_list)
    zone_fields = ["Zone Name"] + ["Channel {}".format(x) for x in range(1, 81)]
    with open("{}/Zones.csv".format(output_dir), "w") as f:
        csvw = csv.DictWriter(f, zone_fields, delimiter=";")
        csvw.writeheader()
        for zone in cp.zones:
            row = {"Zone Name": zone.Name}
            for ix, ch in enumerate(zone.ChannelA + zone.ChannelB):
                if ix + 1 > 80:
                    print("Zone {} exceeds 80 channels".format(zone.Name))
                    break
                row["Channel {}".format(ix + 1)] = ch
            csvw.writerow(row)

