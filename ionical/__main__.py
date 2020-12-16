"""Ionical is a multipurpose CLI tool for icalendar management.  
  - Download ics files, view event data, and track what has
    changed since the ics files were last downloaded
    (eg, to monitor for added or removed events) 
  - Events may be filtered by event summary text or start date.
"""
import argparse
import os
from os.path import abspath
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from textwrap import dedent

import toml

from ionical import __version__
from ionical.ionical import main, sub_cfg


CFG_FN = "ionical_config.toml"
DEF_CFG_DIR = "./"
DEF_ICS_DIR = "./"

DEF_NUM_CHANGELOGS_TO_SHOW = 2

# Default number of days in past for filtering out events
DEF_FILTER_NUM_DAYS_AGO = 1

SAMPLE_CFG_TOML = """# ionical_config.toml

title = "ionical configuration file"
verbose = true

# Note: All options that can be specified/configured on the command line
# may alternatively be specified in this config file. For example, 
# uncommenting 'get_today = true' (below) has the same effect as 
# calling ionical with the '-g' option (i.e., today's ics files will
# be downloaded).  Likewise, uncommenting 'export_csv = ["CAL_1"]' has the 
# same effect as calling ionical with argument/parameter '-i CAL_1'.
# 
# Note: If configuration is specified both in this config file AND via
# a command line argument, the command line argument takes precedence, and
# the information from the config file is ignored.

[actions]
    # restrict_to    = ["CAL_1"]
    # get_today      = true
    # show_schedule  = true
    # show_changelog = true
    # num_changelogs = 2     
    # export_csv     = true   

[filters]
    # earliest       = 2020-11-01
    # latest         = 2021-06-30
    # summary_text   = ["search text 1", "search text two"]

[calendars]

  [calendars.CAL_1]
    description = "BMI Music Industry Events Calendar"
    url         = "https://raw.githubusercontent.com/danyul/ionical/master/tests/ics_dir_test/music_events.ics"
    tz          = "US/Eastern"


[event_classifications]
  [event_classifications.by_start_time]
    [event_classifications.by_start_time.example_time_category]

        Morning     =   [ 
                            [5, 12],   # Any event starting between 5a and 12p 
                        ]              # is categorized as "Morning"
        Afternoon   =   [ 
                            [12, 16],  # Any event starting between 12p and 4p 
                        ]              # is categorized as "Afternoon"
        Evening     =   [ 
                            [16, 20],  # Any event starting between 4p and 8p 
                        ]              # is categorized as "Evening"
        Night       =   [ 
                            [20, 24],  # Any event starting between 8p and midnight, or
                            [0, 4],    # between midnight and 4am is categorized as "Night"
                        ]              #
        All-Day     = "missing"        # If there is no start time, categorize event as "All-Day"
        Other       = "default"        # All other events (in this case, only events starting 
                                       # between 4 and 5 am will be categorized as "Unspecified"


[csv]
    file                 = "ionical_export_default_csv_filename.csv"
    include_empty_dates  = false
    grouping             = "example_time_category"
    order                = ["Morning", "Afternoon"]
    format               = "My morning events: {0} \\n My afternoon events: {1}"
    text_if_not_present  = "I AM AVAILABLE"

    [csv.substitutions]
        "Secret spy meeting with Carl"       = "Going to the zoo"
        "Present shopping to suprise JoJo"   = "Flossing the cat"


# You can tweak the below to change display formatting
[formatting]

    event_summary      = "    {0:16} at {1:10} ({2:<})    {3:30}"
    # Meanings for event_summary fields are as follows:
    #    0: date (further formatted by date_fmt variable)
    #    1: time (further formatted by time_fmt and, if provided, time_replacements)
    #    2: user_defined time grouping (further formatted by time_group_fmt)
    #    3: event summary text
    
    date_fmt           = "%a, %b %d %Y"
    time_fmt           = " %I:%M%p"
    time_replacements  = {" 0" = " ", "(0" = "(", "AM" = "am", "PM" = "pm"}
    time_group         = "example_time_category"
    time_group_fmt     = "{:>} Time"

    # for changelog formatting:
    change_report = "  {label:10}{name:18}{start_str:19} {summary:30} [comp vers:{compare_date}]\\n"


"""


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
            "-h",
            "--help",
            action="store_true",
            help="Print help message, then exit.\n",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help=f"Increase verbosity of feedback messages.\n",
        )
        parser.add_argument(
            "-V",
            "--version",
            action="version",
            help="Print version, then exit.",
            version=__version__,
        )
    if cat == "main":
        parser.add_argument(
            "-g",
            "--get_today",
            action="store_true",
            help=dedent(
                """\
              Download current .ics files and label them with today's
              date. This will be done prior to other actions. 
              (If this is left unspecified, operations will only use
              .ics files that have been previously downloaded.)\n\n"""
            ),
        )
        parser.add_argument(
            "-s",
            "--show",
            action="store_true",
            help="Display events from most recent ical file version for \n"
            "each calendar.\n\n",
        )
        parser.add_argument(
            "-l",
            nargs="?",
            metavar="#_COMPARISONS",
            dest="num_changelogs",
            default=0,
            const=DEF_NUM_CHANGELOGS_TO_SHOW,
            type=valid_pos_integer,
            help=dedent(
                f"""\
              Show changelogs comparing calendar versions from 
              multiple dates. Optionally, specify the number of 
              prior versions (per each calendar) for which to show 
              comparison changelogs. (If left unspecified, 
              #_COMPARISONS default is {DEF_NUM_CHANGELOGS_TO_SHOW}.)\n\n"""
            ),
        )
        parser.add_argument(
            "-c",
            metavar="CSV_FILE",
            dest="csv_file",
            nargs="?",
            const="cfg",
            help="Export calendar events to csv.\n\n",
        )

    if cat == "calendar":
        parser.add_argument(
            "-i",
            metavar="NAME",
            dest="ids",
            nargs="+",
            help="Only operate on calendars with a specified NAME.\n"
            "(If -i not specified, operate on every calendar\n"
            "listed in {CFG_FN}.)\n\n",
        )

    if cat == "path":
        parser.add_argument(
            "-f",
            metavar="CONFIG_DIRECTORY",
            dest="config_dir",
            default=DEF_CFG_DIR,
            help=dedent(
                f"""\
              Directory where config file located.
              The primary config file, {CFG_FN}, should 
              contain a list of calendar names, URLs, and timezones.
              See README for config file format info.
              (Default config directory is user's current directory.)\n\n"""
            ),
        )
        parser.add_argument(
            "-d",
            metavar="ICS_DIR",
            dest="ics_dir",
            help="Directory for downloading or accessing .ics files.\n"
            f"(Default is {DEF_ICS_DIR}.)\n\n",
        )

    if cat == "event":
        parser.add_argument(
            "-a",
            metavar="DATE_OR_NUMBER",
            dest="start_date",
            help=dedent(
                f"""\
                Only include events that start AFTER a specified date.
                (I.e., exclude events starting before the date.)
                Value must be EITHER a date in format YYYY-MM-DD, or 
                a positive integer representing # of days in the past
                (If option unspecified, default behavior is to exclude
                any events starting prior to {DEF_FILTER_NUM_DAYS_AGO
                } {'day' if DEF_FILTER_NUM_DAYS_AGO==1 else 'days'} ago.)
                \n"""
            ),
            type=valid_pos_integer_or_date,
        )
        parser.add_argument(
            "-b",
            metavar="DATE_OR_NUMBER",
            dest="end_date",
            help=dedent(
                """\
                    Only include events that start BEFORE a specified date.
                    (I.e., exclude events starting on or after the date.)
                    Value must be EITHER a date in format YYYY-MM-DD, or 
                    a positive integer representing # of days in the future.
                    (If option unspecified, default behavior is to
                    have no upper limit on event dates.)
                \n"""
            ),
            type=valid_pos_integer_or_date,
        )
        parser.add_argument(
            "-t",
            metavar="TEXT",
            dest="text_filters",
            nargs="+",
            help=dedent(
                """\
                    Only include events whose summary text includes words
                    that match at least one TEXT item.  TEXT items can be
                    either a single word or phrases comprised of words and
                    spaces.  If the latter, you must enclose TEXT within
                    quotation marks.
                    (If option not specified, no text filters are applied.)
                \n"""
            ),
        )


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

    cfg_dir, cfg_fn = args.config_dir, CFG_FN
    using_default_cfg_dir = True if args.config_dir == DEF_CFG_DIR else False
    try:
        with open(Path(cfg_dir) / cfg_fn, "r", encoding="utf-8") as f:
            cfg = toml.loads(f.read())
    except FileNotFoundError:
        print(f"Could not locate {cfg_fn} in {cfg_dir}.")
        if not using_default_cfg_dir:
            print("\nQuitting!\n")
            sys.exit(1)
        else:
            q = "Would you like to create it and populate it with sample data?"
            if query_yes_no(q):
                with open(Path(cfg_dir) / cfg_fn, "w", encoding="utf-8") as f:
                    f.write(SAMPLE_CFG_TOML)
                    print(
                        "File created.\nRun 'ionical -h' to see help message."
                    )
            else:
                print(
                    "OK.  Run 'ionical -h' or see README file if you need help."
                )
        sys.exit(1)

    try:
        cal_tuples = [
            (k, v["description"], v["url"], v["tz"])
            for k, v in cfg["calendars"].items()
        ]
    except KeyError:
        print(
            "A correctly formatted 'calendars' section was not found in\n"
            "the config file.  See README.md file if you need help. \nQuitting.\n"
        )
        sys.exit(1)

    act_cfg = sub_cfg(cfg, "actions")
    fil_cfg = sub_cfg(cfg, "filters")
    verbose_mode = True if args.verbose else sub_cfg(cfg, "verbose", False)
    get_cals = True if args.get_today else sub_cfg(act_cfg, "get_today", False)
    show_cals = True if args.show else sub_cfg(act_cfg, "show_schedule", False)
    c_subset = args.ids if args.ids else sub_cfg(act_cfg, "restrict_to", None)
    ics_dir = (
        args.ics_dir if args.ics_dir else sub_cfg(cfg, "ics_dir", DEF_ICS_DIR)
    )
    if not os.path.isabs(ics_dir):
        ics_dir = Path(cfg_dir) / Path(ics_dir)

    if args.num_changelogs > 0:
        show_changelog = True
        num_changelogs = args.num_changelogs
    else:
        show_changelog = sub_cfg(act_cfg, "show_changelog", False)
        if show_changelog:
            num_changelogs = sub_cfg(
                act_cfg, "num_changelogs", DEF_NUM_CHANGELOGS_TO_SHOW
            )
        else:
            num_changelogs = 0

    csv_export_file = None
    if args.csv_file:
        if args.csv_file == "cfg":
            csv_export_file = sub_cfg(cfg["csv"], "file")
            if not csv_export_file:
                print("Didn't locate 'csv.file' key in cfg.\n  Quitting.\n")
                sys.exit(1)
        else:
            csv_export_file = args.csv_file
    else:
        cfg_says_export = sub_cfg(act_cfg, "export_csv")
        if cfg_says_export:
            csv_export_file = sub_cfg(cfg["csv"], "file")

    if not any([show_cals, show_changelog, get_cals, csv_export_file]):
        print(
            "You MUST specify at least one of the primary options.\n"
            + "\nFor help, run ionical with the -h option.\n"
        )
        sys.exit(1)

    earliest_date, latest_date = None, None
    today = date.today()

    start_date_or_num_days_in_past = (
        args.start_date
        if args.start_date
        else sub_cfg(fil_cfg, "earliest", DEF_FILTER_NUM_DAYS_AGO)
    )
    if isinstance(start_date_or_num_days_in_past, date):
        earliest_date = start_date_or_num_days_in_past
    else:  # it's an int or None
        earliest_date = (
            None
            if start_date_or_num_days_in_past is None
            else today - timedelta(days=start_date_or_num_days_in_past)
        )

    end_date_or_num_days_in_future = (
        args.end_date if args.end_date else sub_cfg(fil_cfg, "latest", None)
    )
    if isinstance(end_date_or_num_days_in_future, date):
        latest_date = end_date_or_num_days_in_future
    else:  # it's an int or None
        latest_date = (
            None
            if end_date_or_num_days_in_future is None
            else today + timedelta(days=end_date_or_num_days_in_future)
        )

    text_filters = (
        args.text_filters
        if args.text_filters
        else sub_cfg(fil_cfg, "summary_text", None)
    )

    if verbose_mode:
        print("\nVerbose mode on.\n")
        if c_subset:
            print(f"\nRestricting all action to calendars: {c_subset}")
        else:
            print(
                "No calendar filters specified. "
                f"Will use all calendars listed in {CFG_FN}."
            )
        print("\nPlanned ionical actions:")
        if get_cals:
            print(f"  Download today's ics files to: {abspath(ics_dir)}")
        if show_cals:
            print(
                "  Print schedule events from the most recent ics version "
                "of each calendar."
            )
        if show_changelog:
            print(
                "  Print changelogs comparing most recent "
                f"{num_changelogs} ics versions of each calendar."
            )
        if csv_export_file:
            print(f"  Export events to CSV file: {abspath(csv_export_file)}")
        print(
            "\nEvent filters to be applied:"
            f"\n  Earliest Date: {earliest_date}"
            f"\n  Latest Date:   {latest_date if latest_date else 'No limit'}"
            "\n  Summary Text:  "
            f"{text_filters if text_filters else 'No text filters'}"
        )

    main(
        cals_data=cal_tuples,
        cfg=cfg,
        verbose_mode=verbose_mode,
        cals_filter=c_subset,
        ics_dir=ics_dir,
        download_option=get_cals,
        show_schedule=show_cals,
        show_changelog=show_changelog,
        csv_export_file=csv_export_file,
        num_changelogs=num_changelogs,  # type: ignore
        earliest_date=earliest_date,
        latest_date=latest_date,
        summary_filters=text_filters,
    )
    print("\n")


if __name__ == "__main__":
    cli()
