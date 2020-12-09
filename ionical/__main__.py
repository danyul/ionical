"""ionical: CLI tool for management of ics schedules --

Download ics calendars, display filtered event
data for a given schedule, show changelogs between ics
schedules from different dates, and convert 
filtered event data to csv format.
"""


import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

from ionical.ionical import main
from . import __version__

ICS_DIR = "./"
DEF_JSON = "./calendar_list.json"
DEF_CONVERSION_TABLE_FILE = "./csv_conversion_table.json"
DEF_DAYSBACK = 1
DEF_NUM_LOOKBACKS = 2

CHANGELOG_DATE_FMT = "%a, %b %d %Y"
CHANGELOG_TIME_FMT = " (%I%p)  "
SHIFT_STR_TEMPLATE = ""
SCHEDULE_SUMMARY_LINE = " {0:16}{1:12}{2:7}{3:30}"
SCHEDULE_EVENT_DATE_FMT = "%a, %b %d %Y"
SCHEDULE_EVENT_TIME_FMT = " %I%p"
SCHEDULE_EVENT_TIME_REPLACEMENTS = {"(0": "(", "AM": "am", "PM": "pm"}

SAMPLE_CALENDAR_LISTING_JSON = """
[
    [
      "BMI", 
      "BMI Music Industry Events Calendar",  
      "https://raw.githubusercontent.com/danyul/ionical/master/tests/ics_dir_test/music_events.ics",
      "US/Eastern"
    ]
]
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


def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, add_help=False
    )
    help_options = parser.add_argument_group("Help/About")
    main_options = parser.add_argument_group(
        "Main Operations (one or more of these MUST be specified)"
    )
    calendar_filter_options = parser.add_argument_group(
        "Calendar Filters (will apply to all Main Operation options)"
    )
    event_filter_options = parser.add_argument_group(
        "Event Filters (for changelogs, schedule viewing, and/or csv exports)"
    )
    file_options = parser.add_argument_group("General Config")
    csv_options = parser.add_argument_group(
        "CSV Export Config (only applicable when -c option also specified)"
    )

    help_options.add_argument(
        "-v",
        "--version",
        action="version",
        help="Print version, then exit (ignoring below options).",
        version=f"{__version__}",
    )
    help_options.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Print help message, then exit (ignoring below options).",
    )
    main_options.add_argument(
        "-g",
        "--get_today",
        action="store_true",
        help="Download current .ics files and label them with today's date. "
        + "\nThis will be done prior to running any other Main Operations. "
        + "\n(If not specified, operations will use only .ics "
        + "files \nwhich have previously been downloaded.)",
    )
    main_options.add_argument(
        "-s",
        "--schedule",
        action="store_true",
        help="Display events from the most recent version of each calendar.",
    )
    main_options.add_argument(
        "-l",
        nargs="?",
        metavar="#_COMPARISONS",
        dest="num_lookbacks",
        default=0,
        const=DEF_NUM_LOOKBACKS,
        type=valid_pos_integer,
        help="Show changelog(s) between schedule versions from multiple dates."
        + "\nOptionally, specify the number of prior versions (per each "
        + "\ncalendar) for which to show comparison changelogs."
        + "\n(If left unspecified, #_COMPARISONS default "
        + f"is {DEF_NUM_LOOKBACKS}.)",
    )
    main_options.add_argument(
        "-c",
        metavar="CSV_EXPORT_FILE",
        dest="csv_file",
        help="Export current schedules to CSV_EXPORT_FILE (alpha status)."
        + "\n(Also, see -x option.)",
    )
    calendar_filter_options.add_argument(
        "-i",
        metavar="CALENDAR_NICKNAMES",
        dest="ids",
        nargs="+",
        help="Only operate on calendars with a nickname identifier that is "
        + "\ngiven in the list of CALENDAR_NICKNAMES."
        + "\n(Nickname identifiers are specified in the calendar list config file "
        + "\nand appear at the start of the filename of downloaded ics files."
        + "\n(Default behavior: no restrictions. I.e., include all calendars.)",
    )
    event_filter_options.add_argument(
        "-t",
        metavar="TEXT_FILTERS",
        dest="text_filters",
        nargs="+",
        help="Only include events with event summaries matching the text "
        + "\nof one or more of the specified TEXT_FILTERS."
        + "\n(Default behavior: no text filters.)",
    )
    event_filter_options.add_argument(
        "-a",
        metavar="DATE_OR_NUMBER",
        dest="start_date",
        help="Only include events that start AFTER a specified date."
        " \nValue must be EITHER a date in format YYYY-MM-DD, or "
        "a positive \ninteger representing # of days in the past."
        f" \n(Default behavior: "
        f"{DEF_DAYSBACK} {'day' if DEF_DAYSBACK==1 else 'days'}"
        " prior to today's date.)",
        default=DEF_DAYSBACK,
        type=valid_pos_integer_or_date,
    )
    event_filter_options.add_argument(
        "-b",
        metavar="DATE_OR_NUMBER",
        dest="end_date",
        help="Only include events that start BEFORE a specified date."
        "\nValue must be EITHER a date in format YYYY-MM-DD, or "
        "a positive \ninteger representing # of days in the future."
        "\n(Default behavior: no filter)",
        type=valid_pos_integer_or_date,
    )
    file_options.add_argument(
        "-f",
        metavar="CAL_CONFIG_FILE",
        dest="calendar_list_file",
        default=DEF_JSON,
        help="File containing list of calendars with basic metadata info."
        + "\n(In JSON format: [[NICKNAME, FULLNAME, URL, TIME_ZONE], ... ] )"
        + f"\n(Default: {DEF_JSON})",
    )
    file_options.add_argument(
        "-d",
        metavar="ICS_DIRECTORY",
        dest="directory",
        default=ICS_DIR,
        help=f"Directory where downloaded .ics files are stored."
        + f"\n(Default: {ICS_DIR})",
    )
    csv_options.add_argument(
        "-x",
        metavar="CONVERSION_FILE",
        dest="csv_conversion_file",
        default=DEF_CONVERSION_TABLE_FILE,
        help="JSON file w/ dictionary of conversion terms. "
        + f"\n(Default: {DEF_CONVERSION_TABLE_FILE}.  If this file "
        + "\n doesn't exist, CSV export will proceed without conversion.)",
    )

    args = parser.parse_args()
    # parser.print_help(file=None)
    # sys.exit(1)
    earliest_date, latest_date = None, None
    show_changelog = True if args.num_lookbacks > 0 else False

    today = date.today()
    using_default_calendar_list = args.calendar_list_file == DEF_JSON
    if args.help:
        parser.print_help()
        sys.exit(1)
    if args.calendar_list_file:
        try:
            print(f"\nCalendar list config file: {args.calendar_list_file}")
            with open(args.calendar_list_file, "r", encoding="utf-8") as f:
                people_tuples = json.loads(f.read())
        except FileNotFoundError:
            if not using_default_calendar_list:
                print(
                    "Could NOT locate the calendar list config file "
                    + f"file: {args.calendar_list_file}"
                )
                print("\n\nQuitting.")
            else:
                print(
                    f"Could NOT find the default calendar list config "
                    + f"file: {args.calendar_list_file}"
                )
                question: str = (
                    "Would you like to create this file and "
                    + "populate it with sample data?"
                )
                if query_yes_no(question):
                    print("\nOK, attempting to create file...")
                    with open(
                        args.calendar_list_file, "w", encoding="utf-8"
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
                        "OK.  To use ionical you'll either need to create/use"
                        "the default calendar list config file, or specify another "
                        "valid config file using the -f option.\n\n"
                        "Run 'ionical -h' for help/instructions."
                    )
            sys.exit(1)
    else:
        print("\nYou must provide a valid calendar list config file.")
        print("Quitting.\n")
        sys.exit(1)
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
    if args.get_today:
        print(
            "\nWill download today's ics files to directory: "
            + f"{args.directory}"
        )

    csv_conversion_dict = {}
    if args.csv_file:
        try:
            print("\nAttempting to write to CSV file: " + f"{args.csv_file}")
            with open(args.csv_conversion_file, "r", encoding="utf-8") as f:
                csv_conversion_dict = json.loads(f.read())
            print(
                "\nFound/using event summary conversion info from: "
                + f"{args.csv_conversion_file}"
            )
        except FileNotFoundError:
            print(
                "\nCould not locate conversion table file:"
                + f"{args.csv_conversion_file}.  Will export events "
                + "to csv without doing any conversions."
            )

    if not any([args.schedule, show_changelog, args.get_today, args.csv_file]):
        print(
            "You MUST specify at least one of the Main Operations.\n"
            + "\nFor help, run ionical with the -h option.\n"
        )
        sys.exit(1)

    if show_changelog:
        date_fmt = CHANGELOG_DATE_FMT
        time_fmt = CHANGELOG_TIME_FMT
    else:
        date_fmt = SCHEDULE_EVENT_DATE_FMT
        time_fmt = SCHEDULE_EVENT_TIME_FMT

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
        csv_file=args.csv_file,
        include_empty_dates=True,
        conversion_table=csv_conversion_dict,
        num_changelog_lookbacks=args.num_lookbacks,
        date_fmt=date_fmt,
        time_fmt=time_fmt,
        time_replacements=SCHEDULE_EVENT_TIME_REPLACEMENTS,
        shift_str_template=SHIFT_STR_TEMPLATE,
        schedule_summary_line=SCHEDULE_SUMMARY_LINE,
    )
    print("\n")


if __name__ == "__main__":
    cli()
