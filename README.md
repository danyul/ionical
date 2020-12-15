
# ionical: Keep an eye on icals!

- ionical is a command line tool (with associated Python  
  libraries) for icalendar management:  
  - Download icalendar files.
  - View schedules, optionally filtered by start date or event   
    summary text.
  - Compare sets of icalendar files obtained on different dates  
    to generate changelogs showing added/removed events.  
  - Classify events based on user-specified criteria  
    (e.g., categorize events whose start time falls between  
    range Xpm-Ypm as being "Workshift A" events, and those  
    between Qpm and Rpm as being "Workshift B" events.)  
  - Export events for multiple calendars to CSV in a 
    user-specified format, filtered on user-specified  
    classications criteria (e.g., workshifts).
- Limitations: 
  - At present, ionical only deals with icalendar start times
    and summary text fields.  Other icalendar fields are ignored.
    This is adequate for many simple use cases (e.g., it was  
    designed to track changes to employee schedules on  
    [Amion](https://amion.com/), and has worked well for that).  
    However, it does not address use cases involving  
    other icalendar fields.
  

## Installing via pip:
```
$ pip install ionical
```
  

## Installing from repository:
```
$ git clone https://github.com/danyul/ionical
$ cd ionical
$ python -m venv env
$ source env/bin/activate
$ pip install -e ".[test]"
```
If on Windows, replace 'source env/bin/activate' with:
```
$ .\env\Scripts\activate
```
  


## Command line usage:
```
Usage: ionical [-v] [-h] [--verbose]
               [-g] [-s] [-l [#_COMPARISONS]] [-c [CSV_FILE]] 
               [-i NAME [NAME ...]] 
               [-a DATE_OR_NUMBER] [-b DATE_OR_NUMBER]
               [-t TEXT [TEXT ...]] 
               [-f CONFIG_DIRECTORY] [-d ICS_DIR] 

Help/About:
  -v, --version        Print version, then exit.
  -h, --help           Print help message, then exit.
  --verbose            Verbose mode.

Primary Options:
  One or more primary options MUST be specified.

  -g, --get_today      Download current .ics files and label them with today's
                       date. This will be done prior to other actions.
                       (If this is left unspecified, operations will only use
                       .ics files that have been previously downloaded.)

  -s, --show           Display events from most recent ical file version for
                       each calendar.

  -l [#_COMPARISONS]   Show changelogs comparing calendar versions from
                       multiple dates. Optionally, specify the number of
                       prior versions (per each calendar) for which to show
                       comparison changelogs.
                       (If left unspecified, #_COMPARISONS default is 2.)

  -c [CSV_FILE]        Export calendar events to csv.


Calendar Filters:
  Restrict all actions to a subset of calendars.

  -i NAME [NAME ...]   Only operate on calendars with a specified NAME.
                       (If -i not specified, operate on every calendar
                       listed in ionical_config.toml.)


Event Filters:
  Filter events shown in changelogs, schedule displays

  -a DATE_OR_NUMBER    Only include events that start AFTER a specified date.
                       (I.e., exclude events starting before the date.)
                       Value must be EITHER a date in format YYYY-MM-DD, or
                       a positive integer representing # of days in the past.
                       (If option unspecified, default behavior is to exclude
                       any events starting prior to 1 day ago.)

  -b DATE_OR_NUMBER    Only include events that start BEFORE a specified date.
                       (I.e., exclude events starting on or after the date.)
                       Value must be EITHER a date in format YYYY-MM-DD, or
                       a positive integer representing # of days in the future.
                       (If option unspecified, default behavior is to
                       have no upper limit on event dates.)

  -t TEXT [TEXT ...]   Only include events whose summary text includes words
                       that match a TEXT item.
                       (If option not specified, no text filters are applied.)


File Locations:
  Specify expected locations for config files and calendar downloads.

  -f CONFIG_DIRECTORY  Directory where config file located.
                       The primary config file, ionical_config.toml, should
                       contain a list of calendar names, URLs, and timezones.
                       See README for config file format info.
                       (Default config directory is user's current directory.)

  -d ICS_DIR           Directory for downloading or accessing .ics files.
                       (Default is ./.)

```

*If installing from repository, replace 'ionical' with 'python -m ionical' 
 in the above usage example.*
   
  
## ionical configuration file:
```
# ionical_config.toml

title = "ionical configuration file"
verbose = true

# Note: All options that can be specified/configured on the command line
# may alternatively be specified in this config file. For example, 
# uncommenting 'get_today = true' (below) has the same effect as 
# calling ionical with the '-g' option (i.e., today's ics files will
# be downloaded).  Likewise, uncommenting 'export_csv = ["BMI"]' has the 
# same effect as calling ionical with argument/parameter '-i BMI'.
# 
# Note: If configuration is specified both in this config file AND via
# a command line argument, the command line argument takes precedence, and
# the information from the config file is ignored.

[actions]
    # get_today      = true
    # restrict_to    = ["BMI"]
    # export_csv     = true   
    # show_schedule  = true
    # show_changelog = true
    # num_changelogs = 2

[filters]
    # earliest       = 2020-11-01
    # latest         = 2022-06-30
    # summary_text   = ["CAL1_NAME"]

[calendars]
  [calendars.CAL1_NAME]
    description = "CAL1_LONG_NAME"
    url = "http://url_to_ics_download_for_CAL_1.ics"
    tz = "US/Eastern"   # or other timezone in pytz format, for CAL1
  [calendars.CAL2_NAME]
    description = "CAL2_LONG_NAME"
    url = "http://url_to_ics_download_for_CAL_2.ics"
    tz = "US/Mountain"   # or other timezone in pytz format, for CAL2


# You can alter the below to change display formatting
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
    change_report      = "  {label:10}{name:18}{start_str:19} {summary:30}   [compare ver: {compare_date}]\n"


[event_classifications]
  [event_classifications.by_start_time]
    [event_classifications.by_start_time.example_time_category]

        Morning     =   [ 
                            [5, 12],   # Any event starting between 5a and 12p is categorized as "Morning"
                        ]  
        Afternoon   =   [ 
                            [12, 16],  # Any event starting between 12p and 4p is categorized as "Afternoon"
                        ]
        Evening     =   [ 
                            [16, 20],  # Any event starting between 4p and 8p is categorized as "Evening"
                        ]
        Night       =   [ 
                            [20, 24],  # Any event starting between 8p and midnight, 
                            [0, 4],    # or between midnight and 5am is categorized as "Night"
                        ]
        All-Day     = "missing"        # If there is no start time, categorize event as "All-Day"
        Other       = "default"        # All other events (in this case, only events starting between 4 and 5 am
                                       # will be labeled "Unspecified"


[csv]
    file                 = "ionical_export_default_csv_filename.csv"
    include_empty_dates  = false
    grouping             = "example_time_category"
    order                = ["Morning", "Afternoon"]
    format               = "My morning events: {0} \n My afternoon events: {1}"
    text_if_not_present  = "I AM AVAILABLE"

    [csv.substitutions]
        "Secret spy meeting with Carl"       = "Going to the zoo"
        "Present shopping to suprise JoJo"   = "Flossing the cat"

```

 - Timezones are in pytz format, e.g., "US/Eastern".  
   Listing of pytz timezones [can be found here](https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones).
 - The calendar **NAME**:
     - Serves as an ID when asking ionical (via -i option)    
       to restrict actions to a subset of calendars.
     - Serves as the leftmost part of the filename for  
       downloaded ics files.
     - Shouldn't have spaces or non-alphanumeric characters.  
 - The calendar **LONG NAME**:
     - Is used for display purposes.
  

## Note on filename format for downloaded ics files:

    Downloaded .ics files have a filename format of   
    ABC123__20200314.ics,  where "ABC123" is a name  
    identifier. (A reasonable name for a calendar  
    which tracks an employee's work schedule might  
    be a last name or an employee ID number.) Names  
    should contain only alphanumeric characters.  
  
    "20200314" indicates that this particular version  
    of the calendar was downloaded on March 14, 2020.  
  

# Libraries used

- [icalendar](https://pypi.org/project/icalendar/)
- [pytz](https://pypi.org/project/pytz/)
- [recurring_ical_events](https://pypi.org/project/recurring-ical-events/)
  (which, in turn, uses [python-dateutil](https://pypi.org/project/python-dateutil/))
  

# Similar projects

- [icalevents](https://github.com/irgangla/icalevents)
  

