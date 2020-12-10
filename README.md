
# Ionical - Keep an eye on icals!

- Ionical is a multipurpose CLI tool for icalendar management:
  - Download ics files, view event data, and compare  
    sets of icalendar files from different dates to 
    generate changelogs showing added/removed events.
  - Events may be filtered by event summary text or start date.
  - Filtered event data may also be exported to CSV (experimental).


## Installing via pip:
```
$ pip install ionical
```


## Installing from respository:
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
Usage: ionical [-v] [-h] 
               [-g] [-s] [-l [#_COMPARISONS]] [-c CSV_EXPORT_FILE] 
               [-i CALENDAR_NICKNAMES [CALENDAR_NICKNAMES ...]] 
               [-t TEXT_FILTERS [TEXT_FILTERS ...]] 
               [-a DATE_OR_NUMBER] [-b DATE_OR_NUMBER]
               [-f CAL_CONFIG_FILE] [-d ICS_DIRECTORY] 
               [-x CONVERSION_FILE]

Help/About:
  -v, --version         Print version, then exit (ignoring below options).
  -h, --help            Print help message, then exit (ignoring below options).

Main Operations (one or more of these MUST be specified):
  -g, --get_today       Download current .ics files and label them with today's date.
                        This will be done prior to running any other Main Operations.
                        (If not specified, operations will use only .ics files
                        which have previously been downloaded.)
  -s, --schedule        Display events from the most recent version of each calendar.
  -l [#_COMPARISONS]    Show changelog(s) between schedule versions from multiple dates.
                        Optionally, specify the number of prior versions (per each
                        calendar) for which to show comparison changelogs.
                        (If left unspecified, #_COMPARISONS default is 2.)
  -c CSV_EXPORT_FILE    Export current schedules to CSV_EXPORT_FILE (alpha status).
                        (Also, see -x option.)

Calendar Filters (will apply to all Main Operation options):
  -i CALENDAR_NICKNAMES [CALENDAR_NICKNAMES ...]
                        Only operate on calendars with a nickname identifier that is
                        given in the list of CALENDAR_NICKNAMES.
                        (Nickname identifiers are specified in the calendar list config file
                        and appear at the start of the filename of downloaded ics files.
                        (Default behavior: no restrictions. I.e., include all calendars.)

Event Filters (for changelogs, schedule viewing, and/or csv exports):
  -t TEXT_FILTERS [TEXT_FILTERS ...]
                        Only include events with event summaries matching the text
                        of one or more of the specified TEXT_FILTERS.
                        (Default behavior: no text filters.)
  -a DATE_OR_NUMBER     Only include events that start AFTER a specified date.
                        Value must be EITHER a date in format YYYY-MM-DD, or a positive
                        integer representing # of days in the past.
                        (Default behavior: 1 day prior to today's date.)
  -b DATE_OR_NUMBER     Only include events that start BEFORE a specified date.
                        Value must be EITHER a date in format YYYY-MM-DD, or a positive
                        integer representing # of days in the future.
                        (Default behavior: no filter)

General Config:
  -f CAL_CONFIG_FILE    File containing list of calendars with basic metadata info.
                        (In JSON format: [[NICKNAME, FULLNAME, URL, TIME_ZONE], ... ] )
                        (Default: ./cals.json)
  -d ICS_DIRECTORY      Directory where downloaded .ics files are stored.
                        (Default: ./)

CSV Export Config (only applicable when -c option also specified):
  -x CONVERSION_FILE    JSON file w/ dictionary of conversion terms.
                        (Default: ./csv_conversions.json.  If this file
                         doesn't exist, CSV export will proceed without conversion.)
```

(If installed from repository, replace 'ionical' with 'python -m ionical' 
 in the above usage example.)


## File format for main configuration file (named cals.json by default):
```
[
  [
    "NAME_FOR_CAL_1", 
    "LONG_NAME_FOR_CAL_1", 
    "http://url_to_ics_download_for_CAL_1.ics", 
    "Timezone_in_pytz_format_for_CAL_1"
  ],
  [
    "NAME_FOR_CAL_2", 
    "LONG_NAME_FOR_CAL_2", 
    "http://url_to_ics_download_for_CAL_2.ics", 
    "Timezone_in_pytz_format_for_CAL_2"
  ],
  ...
]
```
 - Listing of pytz timezones [can be found here](https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones).
 - Calendar **NAME**s:
   - Serve as IDs when telling ionical (via the -i option) to  
     restrict actions to a subset of calendars.
   - Serve as the leftmost part of the filename for downloaded ical files.
   - Should not have any spaces or special non-alphanumeric characters.
 - Calendar **LONG NAME**s:
   - Are used for display

## Filename format for downloaded ics files:

    Downloaded .ics files have a filename format of ABC123__20200314.ics,  
    where "ABC123" is a name identifier for the calendar (a reasonable  
    name for, say, a calendar which tracks an employee's  
    work schedule might be a last name or an employee ID number.) 
    Names shouldn't contain spaces or non-alphanumeric characters.

    "20200314" indicates that this particular version of the calendar   
    was downloaded on March 14, 2020.


# Libraries used

- [icalendar](https://pypi.org/project/icalendar/)
- [pytz](https://pypi.org/project/pytz/)
- [recurring_ical_events](https://pypi.org/project/recurring-ical-events/)
  (which, in turn, uses [python-dateutil](https://pypi.org/project/python-dateutil/))


# Similar projects

- [icalevents](https://github.com/irgangla/icalevents)

