from datetime import date, datetime, timedelta

DEF_ICS_DIR = "./"
DEF_CALS_DIR = "./"
DEF_CALS_FILE = "cals.json"
DEF_DAYSBACK = 1
DEF_NUM_LOOKBACKS = 2
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

def add_calendar_filter_arguments(parser):
    parser.add_argument(
        "-i",
        metavar="NAME",
        dest="ids",
        nargs="+",
        help="Only operate on calendars with a specified NAME."
        + "\n(If -i not specified, operate on every calendar"
        + "\nlisted in cals.json.)\n\n",
    )
            
def add_path_arguments(parser):
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
        "-d",
        metavar="ICS_DIR",
        dest="directory",
        default=DEF_ICS_DIR,
        help=f"Directory for downloading or accessing .ics files.\n\n",
    )
    

def add_event_filter_arguments(parser):
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
 

def date_range_from_args(start,end):
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
