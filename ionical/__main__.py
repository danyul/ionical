import argparse
import json
import sys
from datetime import date, datetime, timedelta

from ionical.ionical import main

ICS_DIR = "./"
DEF_JSON = "./ionical_monitor_list.json"
DEF_CONVERSION_TABLE_FILE = "./ionical_csv_conversions.json"
DEF_DAYSBACK = 1
DEF_NUM_LOOKBACKS = 2

# TODO: GET THESE OUTTA HERE (TIMEZONE, etc)
TIMEZONE = "US/Mountain"

DEF_SAMPLE_CALENDAR_LISTING_JSON = """
[
["NASA", "NASA Launch Schedule",   "http://www.nasa.gov/templateimages/redesign/calendar/iCal/nasa_calendar.ics", "US/Mountain"],
["BMI", "BMI Events Calendar",  "http://bmi.com/events/ical", "US/Mountain"]
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
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    help_options = parser.add_argument_group("Help")
    main_options = parser.add_argument_group(
        "Main Operations "
        + "(can specify one or more, but at least one MUST be specified)"
    )
    event_filter_options = parser.add_argument_group(
        "Filter Options"
        + " (will be applied to all specified Main Operations)"
    )
    file_options = parser.add_argument_group(
        "General File/Directory Configuration Options"
    )
    changelog_options = parser.add_argument_group(
        "Changelog Options (only applicable if -l argument also given)"
    )
    csv_options = parser.add_argument_group(
        "CSV Options (ALPHA/EXPERIMENTAL). Only applicable if -c specified"
    )

    help_options.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Print this help message and exit (ignore other options).",
    )
    main_options.add_argument(
        "-s",
        "--schedule",
        action="store_true",
        help="Display most recent available schedule for each person/entity.",
    )
    main_options.add_argument(
        "-l",
        "--changelog",
        action="store_true",
        help="Show changelog(s) of schedules from multiple dates.",
    )
    main_options.add_argument(
        "-c",
        "--csvfile",
        help="[ALPHA STATUS] Export current schedules to csv file CSVFILE.",
    )
    main_options.add_argument(
        "-g",
        "--gettoday",
        action="store_true",
        help="Download current .ics files and label them with today's date. "
        + "This will be done prior to running any other Main Operations. "
        + "(If not specified, operations will use only those .ics "
        + "files that have been previously downloaded.)",
    )
    event_filter_options.add_argument(
        "-f",
        "--filters",
        nargs="+",
        help="Filter EVENTS by text that appears in event summary field.  "
        + "(Default behavior: no text filters.)",
    )
    event_filter_options.add_argument(
        "-b",
        "--daysback",
        help="Filter out EVENTS occuring before a certain date. "
        " Value needs to be EITHER a date in format YYYY-MM-DD, or "
        " a positive integer representing # of days in past."
        f" (Default behavior: {DEF_DAYSBACK} days before today's date.)",
        default=DEF_DAYSBACK,
        type=valid_pos_integer_or_date,
    )
    event_filter_options.add_argument(
        "-a",
        "--daysahead",
        help="Filter out EVENTS occuring after a certain date. "
        " Value needs to be EITHER a date in format YYYY-MM-DD, or "
        " a positive integer representing # of days in future."
        " (Default behavior: no filter)",
        type=valid_pos_integer_or_date,
    )
    event_filter_options.add_argument(
        "-i",
        "--ids",
        nargs="+",
        help="Filter PEOPLE/ENTITIES to only include those who are specified "
        + " in the given list of IDs. "
        + "(Default behavior: no restrictions; include all IDs)",
    )
    file_options.add_argument(
        "-p",
        "--peoplefile",
        default=DEF_JSON,
        help="JSON config file containing list of scheduled people/entities "
        + "(in format: [[ID1, NAME1, ICS_FEED_URL1, TIME_ZONE1], "
        + "[ID2, NAME2...], ...]). "
        + f"\n(Default: {DEF_JSON})",
    )
    file_options.add_argument(
        "-d",
        "--directory",
        default=ICS_DIR,
        help=f"Directory where .ics files are stored.\n(Default: {ICS_DIR})",
    )
    changelog_options.add_argument(
        "-n",
        "--num_lookbacks",
        help="Number of past schedule versions (per person) to compare.  "
        + "[Only used when displaying changelogs with -l flag.]  "
        + f"(Default behavior: {DEF_NUM_LOOKBACKS} 'lookbacks')",
        default=DEF_NUM_LOOKBACKS,
        type=valid_pos_integer,
    )
    csv_options.add_argument(
        "-t",
        "--csv_conversion_file",
        default=DEF_CONVERSION_TABLE_FILE,
        help="JSON file w/ dictionary of conversion terms. [Only used "
        + "when generating CSV via -c flag.]\n"
        + f"(Default: {DEF_CONVERSION_TABLE_FILE})",
    )

    args = parser.parse_args()

    earliest_date, latest_date = None, None

    today = date.today()
    if args.help:
        parser.print_help()
        sys.exit(1)
    if args.daysback:
        if isinstance(args.daysback, date):
            earliest_date = args.daysback
        else:  # it's an int
            earliest_date = today - timedelta(days=args.daysback)
    if args.daysahead:
        if isinstance(args.daysahead, date):
            latest_date = args.daysahead
        else:  # it's an int
            latest_date = today + timedelta(days=args.daysahead)

    if args.gettoday:
        print(
            "\nWill download today's ics files to directory: "
            + f"{args.directory}"
        )

    if args.peoplefile:
        using_default = args.peoplefile == DEF_JSON
        try:
            lab = "DEFAULT " if using_default else ""
            print(f"\nAttempting to use {lab}listings file: {args.peoplefile}")
            with open(args.peoplefile, "r", encoding="utf-8") as f:
                people_tuples = json.loads(f.read())
        except FileNotFoundError:
            print(f"\nCould not find file {args.peoplefile}.")
            if using_default:
                question: str = "Would you like to create this file"
                " and populate it with sample data, which can "
                " then be edited to meet your needs?"
                if query_yes_no(question):
                    print("\nOK, attempting to create file...\n")
                    with open(args.peoplefile, "w", encoding="utf-8") as f:
                        f.write(DEF_SAMPLE_CALENDAR_LISTING_JSON)
                        print("File created.\nYou could try running:\n"
                        "'ionical -g' to download the latest .ics files, then\n"
                        "'ionical -s' to show future scheduled events.\n")
                else:
                    print("OK, you'll need to specify a data file.")
            print("Quitting.\n")
            sys.exit(1)
    else:
        print("\nYou must provide a valid people file.")
        parser.print_help()
        sys.exit(1)

    csv_conversion_dict = {}
    if args.csvfile:
        try:
            print("\nAttempting to write to CSV file: " + f"{args.csvfile}")
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

    if not any([args.schedule, args.changelog, args.gettoday, args.csvfile]):
        parser.print_help()

        print(
            f"\n\n     {'*'*70}\n"
            + "\n        NOTE: "
            + ".ics filenames will/should have format 123__20200314.ics"
            "\n             "
            + "where 123 is an identifier corresponding to a particular"
            "\n             "
            + "person/entity and 20200314 is the date file was generated.\n"
            + f"\n     {'*'*70}\n"
        )
        sys.exit(1)

    if args.changelog:
        time_replacements = {"(0": "(", "AM": "am", "PM": "pm"}
        date_fmt = "%a, %b %d %Y"
        time_fmt = " (%I%p)  "
    else:
        time_replacements = {"(0": "(", "AM": "am", "PM": "pm"}
        date_fmt = "%a, %b %d %Y"
        time_fmt = " %I%p"

    main(
        people_data=people_tuples,
        download_option=args.gettoday,
        ics_dir=args.directory,
        earliest_date=earliest_date,
        latest_date=latest_date,
        show_schedule=args.schedule,
        show_changelog=args.changelog,
        people_filter=args.ids,
        filters=args.filters,
        csv_file=args.csvfile,
        include_empty_dates=True,
        timezone=TIMEZONE,
        conversion_table=csv_conversion_dict,
        num_changelog_lookbacks=args.num_lookbacks,
        date_fmt=date_fmt,
        time_fmt=time_fmt,
        time_replacements=time_replacements,
        shift_str_template="",
        schedule_summary_line=" {0:16}{1:12}{2:7}{3:30}",
    )
    print("\n")


if __name__ == "__main__":
    cli()
