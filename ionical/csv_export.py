import argparse
import sys
import csv
from pathlib import Path
from collections import OrderedDict
from datetime import date, timedelta  # , tzinfo
from typing import DefaultDict, Dict, List, Optional
from typing import Set

import toml

from ionical.ionical import MonitoredEventData, Person

from ionical.__main__ import (
    __version__,
    DEF_CFG,
    add_args_for_category,
    cals_from_cfg,
    date_range_from_args,
)

SAMPLE_CFG_TOML_W_CSV = """
# ionical configuration file

title = "ionical configuration"

[calendars]
  [calendars.BMI]
    description = "BMI Music Industry Events Calendar"
    url = "https://raw.githubusercontent.com/danyul/ionical/master/tests/ics_dir_test/music_events.ics"
    tz = "US/Eastern"

[csv_substitutions]
    "Phrase One" = "Synonym One"
    "Phrase Two" = "Synonym Two"

"""


class ScheduleWriter:
    def __init__(
        self,
        cals: List[Person],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        filters: Optional[List[str]] = None,
    ):
        self.filters = filters
        self.cals = cals

        self.events_by_person_id: Dict[str, List[MonitoredEventData]] = {
            person.person_id: person.current_schedule.filtered_events(
                earliest_date=earliest_date,
                latest_date=latest_date,
                filters=filters,
            )
            for person in cals
        }

        event_dates = [
            event.forced_date
            for person_id, events in self.events_by_person_id.items()
            for event in events
        ]

        self.earliest_date = (
            earliest_date if earliest_date else min(event_dates)
        )
        self.latest_date = latest_date if latest_date else max(event_dates)

    def csv_write(
        self,
        csv_file,
        csv_dialect: str = "excel",
        include_empty_dates: bool = False,
        conversion_table: Dict[str, str] = None,
        fmt_options=None,
    ):

        try:
            start_time_cat_dict = fmt_options["start_time_cat_dict"]
        except KeyError:
            sys.exit(1)
            #start_time_cat_dict = DEF_START_TIME_CAT_DICT

        # QUICK HACK TO GET IT WORKING - DON'T CRITICIZE!! :)
        # TODO: OBVIOUSLY MAKE GENERALIZABLE and dekludge/dehack
        # https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
        def daterange(start_date, end_date):
            for n in range(int((end_date - start_date).days)):
                yield start_date + timedelta(n)

        if conversion_table is None:
            conversion_table = {}

        def convert_if_lookup_found(summary):
            if summary in conversion_table:
                return conversion_table[summary]
            else:
                return summary

        # TODO: De-HACK!  (Dirty implementation-specific code, to be fixed)
        # DON'T CRITICIZE!
        plists_by_date = OrderedDict([])
        for date_ in daterange(self.earliest_date, self.latest_date):
            plist = list("" for _ in range(len(self.cals)))
            for person in self.cals:
                events = self.events_by_person_id[person.person_id]
                index_ = self.cals.index(person)
                am_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.start_time_cats(start_time_cat_dict)["shift"] == "AM"
                    ),
                    None,
                )
                pm_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.start_time_cats(start_time_cat_dict)["shift"] == "PM"
                    ),
                    None,
                )
                all_day_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.start_time_cats(start_time_cat_dict)["shift"] == "All-Day"
                    ),
                    None,
                )
                text = ""
                if all_day_shift and all([am_shift, pm_shift]):
                    text = "ERROR"
                else:
                    if all_day_shift and not pm_shift:
                        pm_shift = all_day_shift
                    if all_day_shift and not am_shift:
                        am_shift = all_day_shift
                    if am_shift:
                        text = convert_if_lookup_found(am_shift.summary) + "-"
                    if pm_shift and not am_shift:
                        text = "X" + "-"
                    if pm_shift:
                        text += convert_if_lookup_found(pm_shift.summary)
                    if am_shift and not pm_shift:
                        text += "X"
                if am_shift:
                    text = convert_if_lookup_found(am_shift.summary) + "-"
                if pm_shift and not am_shift:
                    text = "O" + "-"
                if pm_shift:
                    text += convert_if_lookup_found(pm_shift.summary)
                if am_shift and not pm_shift:
                    text += "O"
                plist[index_] = text
            if set(plist) != {""} or include_empty_dates:
                plists_by_date[date_] = plist

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect=csv_dialect)
            writer.writerow([""] + [p.person_id for p in self.cals])
            for date_, plist in plists_by_date.items():
                writer.writerow([date_] + plist)


def cli():
    print(f"ionical version: {__version__}")
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    add_args_for_category(parser, "event")
    add_args_for_category(parser, "path")
    add_args_for_category(parser, "calendar")
    parser.add_argument(
        "-c",
        metavar="CSV_FILE",
        dest="csv_file",
        help="Export calendar events to CSV_FILE. (Also see: -x .)\n\n",
    )
    args = parser.parse_args()

    cal_tuples = cals_from_cfg(args.config_dir, DEF_CFG, SAMPLE_CFG_TOML_W_CSV)

    earliest_date, latest_date = date_range_from_args(
        args.start_date, args.end_date
    )
    cfg_fn_path = Path(args.config_dir) / DEF_CFG

    csv_conversion_dict = {}
    if args.csv_file:
        print("\nFilename for CSV export: " + f"{args.csv_file}")
        try:
            with open(cfg_fn_path, "r", encoding="utf-8") as f:
                csv_conversion_dict = toml.loads(f.read())["csv_substitutions"]
            print(f"Found/using 'csv_subtitutions' in {DEF_CFG}.\n")
        except FileNotFoundError:
            print(f"{cfg_fn_path} NOT FOUND! \nQuitting.\n")
            sys.exit(1)
        except KeyError:
            print(f"Note: No 'csv_substitutions' section in {DEF_CFG}.\n")

    all_cals = [
        Person.from_tuple(person_tuple=cal_tuple, ics_dir=args.ics_dir)
        for cal_tuple in cal_tuples
    ]

    if args.ids:
        chosen_cals = [p for p in all_cals if p.person_id in args.ids]
    else:
        chosen_cals = all_cals

    writer = ScheduleWriter(
        cals=chosen_cals,
        earliest_date=earliest_date,
        latest_date=latest_date,
        filters=args.text_filters,
    )

    writer.csv_write(
        conversion_table=csv_conversion_dict,
        csv_file=args.csv_file,
        include_empty_dates=True,
    )


if __name__ == "__main__":
    cli()
