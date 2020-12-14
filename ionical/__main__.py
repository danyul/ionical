"""Ionical is a multipurpose CLI tool for icalendar management.  
  - Download ics files, view event data, and track what has
    changed since the ics files were last downloaded
    (eg, to monitor for added or removed events) 
  - Events may be filtered by event summary text or start date.
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from ionical.ionical import main

import toml

from . import __version__

DEF_CFG = "ionical_config.toml"
DEF_CFG_DIR = "./"
DEF_ICS_DIR = "./"

DEF_DAYSBACK = 1
DEF_NUM_LOOKBACKS = 2
SAMPLE_CFG_TOML = """
# ionical configuration file

title = "ionical configuration"

verbose = true

[calendars]
  [calendars.BMI]
    description = "BMI Music Industry Events Calendar"
    url = "https://raw.githubusercontent.com/danyul/ionical/master/tests/ics_dir_test/music_events.ics"
    tz = "US/Eastern"



# You can alter the below to change display formatting

[formatting]
    event_summary =    "    {0:16} {1:10} ({2:<})    {3:30}"
    date_fmt           = "%a, %b %d %Y"
    time_fmt           = "at %I:%M%p"
    time_group         = "{:>} Time"
    time_replacements  = {" 0" = " ", "(0" = "(", "AM" = "am", "PM" = "pm"}

    # Meanings for event_summary fields are as follows:
    #    0: date (further formatted by date_fmt variable)
    #    1: time (further formatted by time_fmt and, if provided, time_replacements)
    #    2: shift (further formatted by time_group)
    #    3: summary text


[formatting.groupings.start_time.shift]

    Morning     = [ 
                        [5, 12],   # Any event starting between 5a and 12p is categorized as "Morning"
                    ]  
    Afternoon   = [ 
                        [12, 16],  # Any event starting between 12p and 4p is categorized as "Afternoon"
                    ]
    Evening   =   [ 
                        [16, 20],  # Any event starting between 4p and 8p is categorized as "Evening"
                    ]
    Night     =   [ 
                        [20, 24],  # Any event starting between 8p and midnight, 
                        [0, 4],    # or between midnight and 5am is categorized as "Night"
                    ]
    All-Day   = "missing"       # If there is no start time, categorize event as "All-Day"
    Other     = "default"       # All other events (in this case, only events starting between 4 and 5 am
                                #        will be labeled "Unspecified"

[csv]
    include_empty_dates= true


"""


def cfg_from_cfg_file(cfg_dir, cfg_fn):
    cfg_fn_path = Path(cfg_dir) / cfg_fn
    try:
        with open(cfg_fn_path, "r", encoding="utf-8") as f:
            cfg = toml.loads(f.read())
    except FileNotFoundError:
        print("Config file not found. Quitting!\n")
        sys.exit(1)
    except KeyError:
        return None
    return cfg


def cals_from_cfg(cfg_dir, cfg_fn, sample_toml=None):
    using_default_calendar_dir = cfg_dir == DEF_CFG_DIR
    cfg_fn_path = Path(cfg_dir) / cfg_fn

    sample_toml = SAMPLE_CFG_TOML if sample_toml is None else sample_toml

    try:
        with open(cfg_fn_path, "r", encoding="utf-8") as f:
            cfg_dict = toml.loads(f.read())
            cal_tuples = [
                (k, v["description"], v["url"], v["tz"])
                for k, v in cfg_dict["calendars"].items()
            ]
        return cal_tuples
    except FileNotFoundError:
        print(f"Could NOT locate {DEF_CFG} in {cfg_dir}")
        if not using_default_calendar_dir:
            print("\n\nQuitting.")
        else:
            question: str = (
                "Would you like to create this file and "
                + "populate it with sample data?"
            )
            if query_yes_no(question):
                print("\nOK, attempting to create file...")
                with open(cfg_fn_path, "w", encoding="utf-8") as f:
                    f.write(sample_toml)
                    print(
                        "File created.\n\nYou could try running:\n"
                        "'ionical -g' to download the latest .ics files, then\n"
                        "'ionical -s' to show future scheduled events.\n\n"
                        "Run 'ionical -h' for help/instructions."
                    )
            else:
                print(
                    "OK.  To use ionical you'll need to create/use"
                    f" a valid {DEF_CFG} file, \nas described in"
                    " this project's README.\n\n"
                )
        sys.exit(1)


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


# https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n"
            )


def add_args_for_category(main_parser, cat, arg_groups=None):
    if arg_groups == None:
        parser = main_parser
    else:
        parser = arg_groups[cat]

    if cat == "help":
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            help="Print version, then exit.",
            version=f"{__version__}",
        )
        parser.add_argument(
            "-h",
            "--help",
            action="store_true",
            help="Print help message, then exit.\n",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=f"Verbose mode.\n\n",
        )
    if cat == "main":
        parser.add_argument(
            "-g",
            "--get_today",
            action="store_true",
            help="Download current .ics files and label them with today's"
            + "\ndate. This will be done prior to other actions. "
            + "\n(If this is left unspecified, operations will only use"
            + "\n.ics files that have been previously downloaded.)\n\n",
        )
        parser.add_argument(
            "-s",
            "--schedule",
            action="store_true",
            help="Display events from most recent ical file version for "
            + "\neach calendar.\n\n",
        )
        parser.add_argument(
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

    if cat == "calendar":
        parser.add_argument(
            "-i",
            metavar="NAME",
            dest="ids",
            nargs="+",
            help="Only operate on calendars with a specified NAME."
            + "\n(If -i not specified, operate on every calendar"
            + f"\nlisted in {DEF_CFG}.)\n\n",
        )

    if cat == "path":
        parser.add_argument(
            "-f",
            metavar="CONFIG_DIRECTORY",
            dest="config_dir",
            default=DEF_CFG_DIR,
            help=f"Directory where config file located."
            f"\nThe primary config file, {DEF_CFG}, should "
            f"\ncontain a list of calendar names, URLs, and timezones."
            f"\nSee README for config file format info."
            f"\n(Default config directory is user's current directory.)\n\n",
        )
        parser.add_argument(
            "-d",
            metavar="ICS_DIR",
            dest="ics_dir",
            default=DEF_ICS_DIR,
            help=f"Directory for downloading or accessing .ics files.\n\n",
        )

    if cat == "event":
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
            "-t",
            metavar="TEXT",
            dest="text_filters",
            nargs="+",
            help="Only include events whose summary text includes words"
            + "\nthat match a TEXT item."
            + "\n(If option not specified, no text filters are applied.)\n\n",
        )

    if cat == "experimental":
        # parser.add_argument(
        #     "-e",
        #     nargs="+",
        #     metavar="ARG",
        #     dest="experimentals",
        #     help=f"Pass experimental arguments.\n\n",
        # )
        parser.add_argument(
            "-c",
            metavar="CSV_FILE",
            dest="csv_file",
            nargs="?",
            const="cfg",
            help="Export calendar events to csv.\n\n",
        )


def date_range_from_args(start, end):
    today = date.today()
    earliest_date, latest_date = None, None
    if start:
        if isinstance(start, date):
            earliest_date = start
        else:  # it's an int
            earliest_date = today - timedelta(days=start)
    if end:
        if isinstance(end, date):
            latest_date = end
        else:  # it's an int
            latest_date = today + timedelta(days=end)
    return (earliest_date, latest_date)


def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, add_help=False
    )
    help_option_group_info = {
        "help": ["Help/About", None],
        "main": [
            "Primary Options",
            "One or more primary options MUST be specified.",
        ],
        "calendar": [
            "Calendar Filters",
            "Restrict all actions to a subset of calendars.",
        ],
        "event": [
            "Event Filters",
            "Filter events shown in changelogs, schedule displays",
        ],
        "path": [
            "File Locations",
            "Specify expected locations for config files and calendar downloads.",
        ],
        "experimental": [
            "Experimental/Alpha",
            None,
        ],
    }
    option_groups = {}
    for key, (name, desc) in help_option_group_info.items():
        option_groups[key] = parser.add_argument_group(name, desc)

    for key in option_groups.keys():
        add_args_for_category(parser, key, option_groups)

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        sys.exit(1)

    cal_tuples = cals_from_cfg(args.config_dir, DEF_CFG)
    cfg = cfg_from_cfg_file(args.config_dir, DEF_CFG)

    verbose_mode = False
    if args.verbose:
        verbose_mode = True
        print("Operating in verbose mode (--verbose argument passeed).")
    try:
        if cfg["verbose"]:
            verbose_mode = True
            print("Operating in verbose mode (per config file).")
    except KeyError:
        pass

    earliest_date, latest_date = date_range_from_args(
        args.start_date, args.end_date
    )

    if args.get_today and verbose_mode:
        print(
            f"\nWill download today's ics files to directory: {args.ics_dir}"
        )

    show_changelog = True if args.num_lookbacks > 0 else False
    if not any([args.schedule, show_changelog, args.get_today, args.csv_file]):
        print(
            "You MUST specify at least one of the primary options.\n"
            + "\nFor help, run ionical with the -h option.\n"
        )
        sys.exit(1)

    if verbose_mode:
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
                f"Will use all calendars listed in {DEF_CFG}."
            )

    csv_export_file = None
    if args.csv_file:
        if args.csv_file == "cfg":
            try:
                csv_export_file = cfg["csv"]["file"]
            except KeyError:
                print("Didn't locate csv.file in config.\n  Quitting.\n")
                sys.exit(1)
        else:
            csv_export_file = args.csv_file

    main(
        people_data=cal_tuples,
        download_option=args.get_today,
        ics_dir=args.ics_dir,
        earliest_date=earliest_date,
        latest_date=latest_date,
        show_schedule=args.schedule,
        show_changelog=show_changelog,
        people_filter=args.ids,
        csv_export_file=csv_export_file,
        filters=args.text_filters,
        num_lookbacks=args.num_lookbacks,
        cfg=cfg,
        verbose_mode=verbose_mode,
    )


if __name__ == "__main__":
    cli()
