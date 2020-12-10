
# ionical: Keep an eye on icals!

- ionical is a command line tool for icalendar management:  
  - Download icalendar files.
  - View schedules, optionally filtered by start date or event   
    summary text.
  - Compare sets of icalendar files obtained on different dates  
    to generate changelogs showing added/removed events.
  - Export events to CSV.
- Limitations: 
  - At present, ionical only compares and displays event  
    start times and summary text.  Other fields are ignored.  
    While adequate for certain basic use cases (e.g., it was  
    designed to track changes to employee schedules on  
    [Amion](https://amion.com/), and has worked well for that), it cannot   
    handle more sophisticated workflows.  
  

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
Usage: ionical [-v] [-h] 
               [-g] [-s] [-l [#_COMPARISONS]] [-c CSV_EXPORT_FILE] 
               [-i NAME [NAME ...]] 
               [-t TEXT [TEXT ...]] 
               [-a DATE_OR_NUMBER] [-b DATE_OR_NUMBER]
               [-f CALS_CFG_DIR] [-d ICS_DIR] 
               [-x CONVERSION_FILE]

Primary Options:
  One or more primary options MUST be specified.

  -g, --get_today     Download current .ics files and label them with today's
                      date. This will be done prior to other actions.
                      (If this is left unspecified, operations will only use
                      .ics files that have been previously downloaded.)

  -s, --schedule      Display events from most recent ical file version for
                      each calendar.

  -l [#_COMPARISONS]  Show changelogs comparing calendar versions from
                      multiple dates. Optionally, specify the number of
                      prior versions (per each calendar) for which to show
                      comparison changelogs.
                      (If left unspecified, #_COMPARISONS default is 2.)

  -c CSV_FILE         Export calendar events to CSV_FILE (also, see -x).


Calendar Filters:
  Restrict all actions to a subset of calendars.

  -i NAME [NAME ...]  Only operate on calendars with a specified NAME.
                      (If -i not specified, operate on every calendar
                      listed in cals.json.)


Event Filters:
  Filter events shown in changelogs, schedule displays, and CSV exports.

  -t TEXT [TEXT ...]  Only include events whose summary text includes words
                      that match a TEXT item.
                      (If option not specified, no text filters are applied.)

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
                      (If option unspecified, default behavior is to
                      have no upper limit on event dates.)


General Config:
  Specify expected file locations, if different from the current directory.

  -f CALS_CFG_DIR     Directory where primary config file cals.json located.
                      cals.json should contain a list of calendar names,
                      URLs, and timezones.  See README for specifications.

  -d ICS_DIR          Directory for downloading/accessing .ics files.


CSV Export Config:
  Applicable only when -c option also specified.

  -x CONVERSION_FILE  JSON file w/ dictionary of conversion terms.
                      (Default: ./csv_conversions.json.  If file doesn't
                      exist, CSV export will proceed without conversion.)

```

*If installing from repository, replace 'ionical' with 'python -m ionical' 
 in the above usage example.*
   
  
## File format for cals.json (ionical's primary configuration file):
```
[
  [
    "NAME_for_CAL_1", 
    "LONG_NAME_for_CAL_1", 
    "http://url_to_ics_download_for_CAL_1.ics", 
    "Timezone_in_pytz_format_for_CAL_1"
  ],
  [
    "NAME_for_CAL_2", 
    "LONG_NAME_for_CAL_2", 
    "http://url_to_ics_download_for_CAL_2.ics", 
    "Timezone_in_pytz_format_for_CAL_2"
  ],
  ...
]
```
 - Listing of pytz timezones [can be found here](https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones).
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
  

