
# ionical: Keep an eye on icals!


- **ionical** is a command line tool for tracking schedule changes  
    in iCalendar feeds (downloadable .ics files):  
  - Download and compare sets of iCalendar files obtained on   
    different dates to generate changelogs of added/removed events.  
  - View current schedules, optionally filtered by start date  
    or event summary text.
  - Classify events based on user-specified criteria  
    (e.g., categorize events whose start time falls between  
    range Xpm-Ypm as being "Workshift A" events, and those with  
    start times in a different range as "Workshift B" events).  
  - Export filtered events from calendars to CSV files,  
    using user-specified filter criteria (e.g., workshifts)  
    and user-specified formatting.  
- Limitations: 
  - ionical only deals with iCalendar start times  
    and summary text fields, and ignores other fields.  
    This proves adequate for many simple use cases (e.g., it was  
    designed to track changes to employee schedules on  
    [Amion](https://amion.com/), and has worked well for that).  For iCalendar management  
    involving additional fields or more complex use cases, you'll need to  
    look at other tools (or submit a pull request! :) ).
    


## Installing via pip:
```
$ pip install ionical
$ ionical
```
- The first time you run ionical there will be no  
  ionical_config.toml file present, and you'll be  
  prompted to generate one (in the current directory).  
  Once it is created, you can add the names and URLs  
  for calendars you want to track/monitor, and specify  
  multilple other configuration options. 
  
  
## Installing for development from GitHub:
```
$ git clone https://github.com/danyul/ionical
$ cd ionical
$ python3 -m venv env
$ source env/bin/activate
$ pip install -e ".[dev]"
$ python -m ionical
```
- If on Windows, replace:
  - **'source env/bin/activate'** with **'.\env\Scripts\activate'**
  - **'python3'** with **'python'**

  
## Command line usage ('ionical -h' output):
```


Usage: ionical [-h] [-v] [-V]
               [-f CONFIG_DIRECTORY] [-d ICS_DIR]
               [-g] [-s] [-l [#_COMPARISONS]] [-c [CSV_FILE]]
               [-i NAME [NAME ...]]
               [-a DATE_OR_NUMBER] [-b DATE_OR_NUMBER] [-t TEXT [TEXT ...]]

Keep an eye on ical!  ionical is a CLI tool to track iCalendar changes.

Help/About:
  -h, --help           Print help message, then exit.
  -v, --verbose        Increase the level of printed feeedback.
  -V, --version        Print version, then exit.

File Locations:
  Specify expected locations for config files and calendar downloads.

  -f CONFIG_DIRECTORY  Directory where config file ionical_config.toml located.
                       This file will contain basic calendar information
                       (names, URLs for .ics files, and timezones) and allows
                       various additional configuration options.
                       See README file for an example, or run 'ionical' to
                       generate a sample config file which may then be edited.
                       (default: current directory)

  -d ICS_DIR           Directory for downloading/accessing .ics files.
                       (default: current directory)


Actions:
  One or more action options MUST be specified.

  -g, --get_today      Download current .ics files and label them with today's
                       date. This will be done prior to other actions.
                       (If this is left unspecified, operations will only use
                       .ics files that have been previously downloaded.)

  -s, --show           Display events from most recent ical file version for
                       each calendar.

  -l [#_COMPARISONS]   Show changelogs comparing calendar versions from
                       multiple dates. Optionally, specify the number of
                       prior versions (per each calendar) for which to show
                       comparison changelogs. (If left unspecified,
                       #_COMPARISONS default is 2.)

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
                       a positive integer representing # of days in the past
                       (If option unspecified, default behavior is to exclude
                       any events starting prior to 1 day ago.)

  -b DATE_OR_NUMBER    Only include events that start BEFORE a specified date.
                       (I.e., exclude events starting on or after the date.)
                       Value must be EITHER a date in format YYYY-MM-DD, or
                       a positive integer representing # of days in the future.
                       (If option unspecified, default behavior is to
                       have no upper limit on event dates.)

  -t TEXT [TEXT ...]   Only include events whose summary text includes words
                       that match at least one TEXT item.  TEXT items can be
                       either a single word or phrases comprised of words and
                       spaces.  If the latter, you must enclose TEXT within
                       quotation marks.
                       (If option not specified, no text filters are applied.)

```

   
  
## ionical configuration file:
```
# ionical_config.toml

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
    # latest         = 2022-06-30
    # summary_text   = ["search text 1", "search text two"]


[calendars]

  [calendars.CAL1_NAME]
    description = "CAL1_LONG_NAME"
    url = "http://url_to_ics_download_for_CAL_1.ics"
    tz = "US/Eastern"   # or other timezone in pytz format, for CAL1

  [calendars.CAL2_NAME]
    description = "CAL2_LONG_NAME"
    url = "http://url_to_ics_download_for_CAL_2.ics"
    tz = "US/Mountain"   # or other timezone in pytz format, for CAL2


[event_classifications]
  [event_classifications.by_start_time]
    [event_classifications.by_start_time.example_time_category]

        Morning    =  [ 
                        [5, 12],   # Any event starting between 5am and 12pm 
                      ]            # is categorized as "Morning"
        Afternoon  =  [ 
                        [12, 16],  # Any event starting between 12p and 4pm 
                      ]            # is categorized as "Afternoon"
        Evening    =  [ 
                        [16, 20],  # Any event starting between 4pm and 8pm
                      ]            # is categorized as "Evening"
        Night      =  [ 
                        [20, 24],  # Any event that starts between 8pm
                        [ 0,  4],  # and 4am is categorized as "Night"
                      ]            
        All-Day    = "missing"     # If no start time, categorize as "All-Day"
        Other      = "default"     # All other events (in this case, only 
                                   # events starting between 4 and 5 am) will 
                                   # be categorized as "Unspecified".


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
    change_report = "  {label:10}{name:18}{start_str:19} {summary:30} [comp vers:{compare_date}]\n"



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
- [toml](https://pypi.org/project/toml/)

# Related projects 

- [icalevents](https://github.com/irgangla/icalevents)
- [gcalcii](https://github.com/insanum/gcalcli)
- [vobject](https://pypi.org/project/vobject/)
