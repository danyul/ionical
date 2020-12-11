"""Ionical is a multipurpose CLI tool for icalendar management.  
  - Download ics files, view event data, and track what has
    changed since the ics files were last downloaded
    (eg, to monitor for added or removed events) 
  - Events may be filtered by event summary text or start date.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import ionical.cli_helpers
from ionical.ionical import main
from . import __version__

DEF_ICS_DIR = ionical.cli_helpers.DEF_ICS_DIR
DEF_CALS_DIR = ionical.cli_helpers.DEF_CALS_DIR
DEF_CALS_FILE = ionical.cli_helpers.DEF_CALS_FILE
DEF_DAYSBACK = ionical.cli_helpers.DEF_DAYSBACK
DEF_NUM_LOOKBACKS = ionical.cli_helpers.DEF_NUM_LOOKBACKS
SAMPLE_CALENDAR_LISTING_JSON = ionical.cli_helpers.SAMPLE_CALENDAR_LISTING_JSON

valid_date = ionical.cli_helpers.valid_date
valid_pos_integer_or_date = ionical.cli_helpers.valid_pos_integer_or_date
valid_pos_integer = ionical.cli_helpers.valid_pos_integer
query_yes_no = ionical.cli_helpers.query_yes_no

def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, add_help=False
    )
    help_options = parser.add_argument_group("Help/About")
    main_options = parser.add_argument_group(
        "Primary Options", "One or more primary options MUST be specified."
    )
    calendar_filter_options = parser.add_argument_group(
        "Calendar Filters",
        "Restrict all actions to a subset of calendars.",
    )
    event_filter_options = parser.add_argument_group(
        "Event Filters",
        "Filter events shown in changelogs, schedule displays, ",
    )
    file_options = parser.add_argument_group(
        "File Locations",
        "Specify expected locations for config files and calendar downloads.",
    )
    experimental_options = parser.add_argument_group(
        "Experimental",
    )

    help_options.add_argument(
        "-v",
        "--version",
        action="version",
        help="Print version, then exit.",
        version=f"{__version__}",
    )
    help_options.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Print help message, then exit.\n\n",
    )
    main_options.add_argument(
        "-g",
        "--get_today",
        action="store_true",
        help="Download current .ics files and label them with today's"
        + "\ndate. This will be done prior to other actions. "
        + "\n(If this is left unspecified, operations will only use"
        + "\n.ics files that have been previously downloaded.)\n\n",
    )
    main_options.add_argument(
        "-s",
        "--schedule",
        action="store_true",
        help="Display events from most recent ical file version for "
        + "\neach calendar.\n\n",
    )
    main_options.add_argument(
        "-l",
        nargs="?",
        metavar="#_COMPARISONS",
        dest="num_lookbacks",
        default=0,
        const=DEF_NUM_LOOKBACKS,
        type=valid_pos_integer,
        help="Show changelogs comparing calendar versions from "
        "\nmultiple dates. Optionally, specify the number of "
        "\nprior versions (per each calendar) for which to show "
        "\ncomparison changelogs. \n(If left unspecified, "
        f"#_COMPARISONS default is {DEF_NUM_LOOKBACKS}.)\n\n",
    )

    ionical.cli_helpers.add_event_filter_arguments(event_filter_options)
    ionical.cli_helpers.add_path_arguments(file_options)
    ionical.cli_helpers.add_calendar_filter_arguments(calendar_filter_options)

    experimental_options.add_argument(
        "--verbose",
        action="store_true",
        help=f"Verbose mode.\n",
    )
    experimental_options.add_argument(
        "-e",
        nargs="+",
        metavar="ARG",
        dest="experimentals",
        help=f"Pass experimental arguments.\n\n",
    )

    args = parser.parse_args()
    earliest_date, latest_date = None, None
    show_changelog = True if args.num_lookbacks > 0 else False

    using_default_calendar_dir = args.config_dir == DEF_CALS_DIR
    if args.help:
        parser.print_help()
        sys.exit(1)
    if args.config_dir:
        try:
            with open(
                Path(args.config_dir) / DEF_CALS_FILE,
                "r",
                encoding="utf-8",
            ) as f:
                people_tuples = json.loads(f.read())
        except FileNotFoundError:
            print(
                f"Could NOT locate {DEF_CALS_FILE} in " + f"{args.config_dir}"
            )
            if not using_default_calendar_dir:
                print("\n\nQuitting.")
            else:
                question: str = (
                    "Would you like to create this file and "
                    + "populate it with sample data?"
                )
                if query_yes_no(question):
                    print("\nOK, attempting to create file...")
                    with open(
                        Path(args.config_dir) / DEF_CALS_FILE,
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(SAMPLE_CALENDAR_LISTING_JSON)
                        print(
                            "File created.\n\nYou could try running:\n"
                            "'ionical -g' to download the latest .ics files, then\n"
                            "'ionical -s' to show future scheduled events.\n\n"
                            "Run 'ionical -h' for help/instructions."
                        )
                else:
                    print(
                        "OK.  To use ionical you'll need to create/use"
                        " a valid cals.json file, \nas described in"
                        " this project's README.\n\n"
                    )
            sys.exit(1)
    else:
        print(f"\nYou must provide a valid directory for {DEF_CALS_FILE}")
        print("\nQuitting.\n")
        sys.exit(1)
    
    earliest_date, latest_date = ionical.cli_helpers.date_range_from_args(
        args.start_date, args.end_date
    )

    if args.get_today and args.verbose:
        print(
            "\nWill download today's ics files to directory: "
            + f"{args.directory}"
        )

    if not any([args.schedule, show_changelog, args.get_today]):
        print(
            "You MUST specify at least one of the primary options.\n"
            + "\nFor help, run ionical with the -h option.\n"
        )
        sys.exit(1)

    # Schdule Summary Line Field Variables
    # 0: date (further formatted by date_fmt variable)
    # 1: time (further formatted by time_fmt and time_replacements dict)
    # 2: shift (further formatted by shift_str_template)
    # 3: summary text

    if args.experimentals:
        shift_str_template, event_summary_fmt = args.experimentals
    else:
        # "Shift: {:11}", " {0:16}{1:12}{2:7}{3:30}"
        shift_str_template, event_summary_fmt = "", "    {0:16}  {1:12}{3:30}"

    date_fmt = "%a, %b %d %Y"
    time_fmt = " (%I%p)  " if show_changelog else " %I%p"
    time_replacements = {
        " 0": " ",
        "(0": "(",
        "AM": "am",
        "PM": "pm",
    }

    if args.verbose:
        print(
            "\nEvent filters to be applied:\n"
            f"  Earliest Date: {earliest_date}\n"
            f"  Latest Date:   {latest_date if latest_date else 'No limit'}\n"
            "  Summary Text:  "
            f"{args.text_filters if args.text_filters else 'No text filters'}\n"
        )

        if args.ids:
            print(f"Restricting actions to calendars: {args.ids}\n")
        else:
            print(
                "No calendar filters specified. "
                f"Will use all calendars listed in {DEF_CALS_FILE}."
            )

    main(
        people_data=people_tuples,
        download_option=args.get_today,
        ics_dir=args.directory,
        earliest_date=earliest_date,
        latest_date=latest_date,
        show_schedule=args.schedule,
        show_changelog=show_changelog,
        people_filter=args.ids,
        filters=args.text_filters,
        include_empty_dates=True,
        num_changelog_lookbacks=args.num_lookbacks,
        date_fmt=date_fmt,
        time_fmt=time_fmt,
        time_replacements=time_replacements,
        shift_str_template=shift_str_template,
        schedule_summary_line=event_summary_fmt,
    )
    print("\n")


if __name__ == "__main__":
    cli()
