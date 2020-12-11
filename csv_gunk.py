import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import re
import sys
from collections import OrderedDict, defaultdict
from datetime import date, datetime, time, timedelta  # , tzinfo
from pathlib import Path
from typing import DefaultDict, Dict, List, NamedTuple, Optional
from typing import Set, Tuple

import ionical.cli_helpers

from ionical.ionical import MonitoredEventData, Person
from ionical import __version__

from ionical.cli_helpers import (
    DEF_CALS_DIR,
    DEF_CALS_FILE,
    DEF_ICS_DIR,
    DEF_DAYSBACK,
    DEF_NUM_LOOKBACKS,
    SAMPLE_CALENDAR_LISTING_JSON,
    valid_date,
    valid_pos_integer,
    valid_pos_integer_or_date,
    query_yes_no,
    add_event_filter_arguments,
    add_calendar_filter_arguments,
    add_path_arguments,
)


def cli():
    print(f"ionical version: {__version__}")
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    add_event_filter_arguments(parser)
    add_path_arguments(parser)
    add_calendar_filter_arguments(parser)
    parser.add_argument(
        "-c",
        metavar="CSV_FILE",
        dest="csv_file",
        help="Export calendar events to CSV_FILE. (Also see: -x .)\n\n",
    )
    parser.add_argument(
        "-x",
        metavar="CONVERSION_FILE",
        dest="convert_file",
        help="Path to event summary conversion file for CSV export.",
    )
    args = parser.parse_args()

    try:
        with open(
            Path(args.config_dir) / DEF_CALS_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            people_tuples = json.loads(f.read())
    except FileNotFoundError:
        print(f"Could NOT locate {DEF_CALS_FILE} in " + f"{args.config_dir}")

    earliest_date, latest_date = ionical.cli_helpers.date_range_from_args(
        args.start_date, args.end_date
    )

    csv_conversion_dict = {}
    if args.csv_file:
        print("\nFilename for CSV export: " + f"{args.csv_file}")
        if args.convert_file:
            print(f"CSV export conversion file specified: {args.convert_file}")
            try:
                with open(Path(args.convert_file), "r", encoding="utf-8") as f:
                    csv_conversion_dict = json.loads(f.read())
                print("CSV conversion file successfully located.\n")
            except FileNotFoundError:
                print("However, CSV conversion file NOT FOUND! \nQuitting.\n")
                sys.exit(1)

    all_people = [
        Person.from_tuple(person_tuple=person_tuple, ics_dir=args.directory)
        for person_tuple in people_tuples
    ]

    if args.ids:
        chosen_people = [p for p in all_people if p.person_id in args.ids]
    else:
        chosen_people = all_people

    writer = ScheduleWriter(
        people=chosen_people,
        earliest_date=earliest_date,
        latest_date=latest_date,
        filters=args.text_filters,
    )

    writer.csv_write(
        conversion_table=csv_conversion_dict,
        csv_file=args.csv_file,
        include_empty_dates=True,
    )


class ScheduleWriter:
    def __init__(
        self,
        people: List[Person],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        filters: Optional[List[str]] = None,
    ):
        self.filters = filters
        self.people = people

        self.events_by_person_id: Dict[str, List[MonitoredEventData]] = {
            person.person_id: person.current_schedule.filtered_events(
                earliest_date=earliest_date,
                latest_date=latest_date,
                filters=filters,
            )
            for person in people
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
        **kwargs,
    ):

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
            plist = list("" for _ in range(len(self.people)))
            for person in self.people:
                events = self.events_by_person_id[person.person_id]
                index_ = self.people.index(person)
                am_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "AM"
                    ),
                    None,
                )
                pm_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "PM"
                    ),
                    None,
                )
                all_day_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "All-Day"
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
            writer.writerow([""] + [p.person_id for p in self.people])
            for date_, plist in plists_by_date.items():
                writer.writerow([date_] + plist)


if __name__ == "__main__":
    cli()
