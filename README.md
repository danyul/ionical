
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
               [-i NAME [NAME ...]] 
               [-t TEXT [TEXT ...]] 
               [-a DATE_OR_NUMBER] [-b DATE_OR_NUMBER]
               [-f CALS_CFG_DIR] [-d ICS_DIR] 
               [-x CONVERSION_FILE]

Help/About:
  -v, —version       Print version, then exit (ignoring below options).
  -h, —help          Print help message, then exit (ignoring below options).

Primary Options:
  One or more primary options MUST be specified.

  -g, —get_today     Download current .ics files and label them with today’s date. 
                      This will be done prior to the other primary options. 
                      (If this option is left unspecified, operations will 
                      use only those .ics files that have been previously downloaded.)
  -s, —schedule      Display events from the most recent version of each calendar.
  -l [#_COMPARISONS]  Show changelog(s) between schedule versions from multiple dates.
                      Optionally, specify the number of prior versions (per each 
                      calendar) for which to show comparison changelogs.
                      (If left unspecified, #_COMPARISONS default is 2.)
  -c CSV_EXPORT_FILE  Export current schedules to CSV_EXPORT_FILE (also, see -x option).

Calendar Filters:
  Restrict actions to a subset of calendars (affects all primary options).

  -i NAME [NAME ...]  Only operate on calendars with a specified NAME.
                      (If -i not specified, operate on every calendar
                      listed in cals.json.)

Event Filters:
  Filter events shown in changelogs, schedule displays, and csv exports.

  -t TEXT [TEXT ...]  Only include events whose summaries containing matching text.
                      (If option unspecified, no text filters are applied.)
  -a DATE_OR_NUMBER   Only include events that start AFTER a specified date.
                      (I.e., exclude events starting before the date.) 
                      Value must be EITHER a date in format YYYY-MM-DD, or 
                      a positive integer representing # of days in the past.
                      (If option unspecified, default behavior is to exclude
                      any events starting prior to 1 day ago.)
  -b DATE_OR_NUMBER   Only include events that start BEFORE a specified date.
                      (I.e., exclude events starting on or after the date.)
                      Value must be EITHER a date in format YYYY-MM-DD, or 
                      a positive integer representing # of days in the future.
                      (If option unspecified, no ‘latest date’ limit will be applied.)

General Config:
  Specify expected file locations, if different than the current directory.

  -f CALS_CFG_DIR     Location of cals.json, which contains a listing of
                      calendars and their metadata.  See Readme for specifications.
                      (Default: ./)
  -d ICS_DIR          Directory where downloaded .ics files are to be stored/accessed.
                      (Default: ./)

CSV Export Config:
  Applicable only when -c option also specified.

  -x CONVERSION_FILE  JSON file w/ dictionary of conversion terms. 
                      (Default: ./csv_conversions.json.  If this file 
                      doesn’t exist, CSV export will proceed without conversion.)
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
 - The calendar **NAME**:
     - Serves as an ID when instructing ionical (via -i) to  
       restrict actions to a subset of calendars.
     - Serves as the leftmost part of the filename for downloaded ical files.
     - Should not have any spaces or non-alphanumeric characters.
 - The calendar **LONG NAME**:
     - Is used for display purposes.

## Filename format for downloaded ics files:

    Downloaded .ics files have a filename format of ABC123__20200314.ics,  
    where "ABC123" is a Name identifier. (A reasonable  
    name for a calendar which tracks an employee's  
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

