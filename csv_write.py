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

from ionical.ionical import Person

ICS_DIR = "./"
DEF_CALS_DIR = "./"
DEF_CALS_FILE = "cals.json"
DEF_DAYSBACK = 1
DEF_NUM_LOOKBACKS = 2


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = (
            "Not a valid date: '{0}'.".format(s)
            + "  Should be in format YYYY-MM-DD."
        )
        raise argparse.ArgumentTypeError(msg)


def valid_pos_integer_or_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        try:
            ivalue = int(value)
            msg = (
                f"{value} is not a valid argument."
                + " Needs to be either a positive integer or a date in"
                + " the format YYYY-MM-DD."
            )
            if ivalue <= 0:
                raise argparse.ArgumentTypeError(msg)
            return ivalue
        except ValueError:
            raise argparse.ArgumentTypeError(msg)


def valid_pos_integer(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Needs to be a positive integer.")
    return ivalue


def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, add_help=False
    )
    parser.add_argument(
        "-f",
        metavar="CONFIG_DIRECTORY",
        dest="config_dir",
        default=DEF_CALS_DIR,
        help=f"Directory where config files located."
        f"\nThe primary config file, {DEF_CALS_FILE}, should "
        f"\ncontain a list of calendar names, URLs, and timezones."
        f"\nSee README for config file format info."
        f"\n(Default config directory is user's current directory.)\n\n",
    )
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
    parser.add_argument(
        "-i",
        metavar="NAME",
        dest="ids",
        nargs="+",
        help="Only operate on calendars with a specified NAME."
        + "\n(If -i not specified, operate on every calendar"
        + "\nlisted in cals.json.)\n\n",
    )
    parser.add_argument(
        "-t",
        metavar="TEXT",
        dest="text_filters",
        nargs="+",
        help="Only include events whose summary text includes words"
        + "\nthat match a TEXT item."
        + "\n(If option not specified, no text filters are applied.)\n\n",
    )
    parser.add_argument(
        "-a",
        metavar="DATE_OR_NUMBER",
        dest="start_date",
        help="Only include events that start AFTER a specified date."
        "\n(I.e., exclude events starting before the date.)"
        " \nValue must be EITHER a date in format YYYY-MM-DD, or "
        "\na positive integer representing # of days in the past."
        f"\n(If option unspecified, default behavior is to exclude"
        f"\nany events starting prior to "
        f"{DEF_DAYSBACK} {'day' if DEF_DAYSBACK==1 else 'days'} ago.)\n\n",
        default=DEF_DAYSBACK,
        type=valid_pos_integer_or_date,
    )
    parser.add_argument(
        "-b",
        metavar="DATE_OR_NUMBER",
        dest="end_date",
        help="Only include events that start BEFORE a specified date."
        "\n(I.e., exclude events starting on or after the date.)"
        "\nValue must be EITHER a date in format YYYY-MM-DD, or "
        "\na positive integer representing # of days in the future."
        "\n(If option unspecified, default behavior is to"
        "\nhave no upper limit on event dates.)\n\n",
        type=valid_pos_integer_or_date,
    )
    parser.add_argument(
        "-d",
        metavar="ICS_DIR",
        dest="directory",
        default=ICS_DIR,
        help=f"Directory for downloading or accessing .ics files.\n\n",
    )
    args = parser.parse_args()
    earliest_date, latest_date = None, None
    today = date.today()

    try:
        with open(
            Path(args.config_dir) / DEF_CALS_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            people_tuples = json.loads(f.read())
    except FileNotFoundError:
        print(f"Could NOT locate {DEF_CALS_FILE} in " + f"{args.config_dir}")
    if args.start_date:
        if isinstance(args.start_date, date):
            earliest_date = args.start_date
        else:  # it's an int
            earliest_date = today - timedelta(days=args.start_date)
    if args.end_date:
        if isinstance(args.end_date, date):
            latest_date = args.end_date
        else:  # it's an int
            latest_date = today + timedelta(days=args.end_date)

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
    writer.csv_write(csv_file=args.csv_file, include_empty_dates=True)


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
