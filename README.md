
# Ionical - keeping an eye on icals

## Installing via pip:
```
$ pip install ionical
```

## Command line usage:
```
ionical [-h] [-s] [-l] [-c CSVFILE] [-g] 
                  [-f FILTERS [FILTERS ...]] [-b DAYSBACK] [-a DAYSAHEAD] [-i IDS [IDS ...]] 
                  [-d DIRECTORY] [-p PEOPLEFILE] 
                  [-n NUM_LOOKBACKS] 
                  [-t CSV_CONVERSION_FILE]
Help:
  -h, --help            Print this help message and exit (ignore other options).

Main Operations (can specify one or more, but at least one MUST be specified):
  -s, --schedule        Display most recent available schedule for each person/entity.
  -l, --changelog       Show changelog(s) of schedules from multiple dates.
  -c CSVFILE, --csvfile CSVFILE
                        [ALPHA STATUS] Export current schedules to csv file CSVFILE.
  -g, --gettoday        Download current .ics files and label them with today's date. This will be done prior to running any other Main
                        Operations. (If not specified, operations will use only those .ics files that have been previously downloaded.)

Filter Options (will be applied to all specified Main Operations):
  -f FILTERS [FILTERS ...], --filters FILTERS [FILTERS ...]
                        Filter EVENTS by text that appears in event summary field. (Default behavior: no text filters.)
  -b DAYSBACK, --daysback DAYSBACK
                        Filter out EVENTS occuring before a certain date. Value needs to be EITHER a date in format YYYY-MM-DD, or a positive
                        integer representing # of days in past. (Default behavior: 0 days before today's date.)
  -a DAYSAHEAD, --daysahead DAYSAHEAD
                        Filter out EVENTS occuring after a certain date. Value needs to be EITHER a date in format YYYY-MM-DD, or a positive
                        integer representing # of days in future. (Default behavior: no filter)
  -i IDS [IDS ...], --ids IDS [IDS ...]
                        Filter PEOPLE/ENTITIES to only include those who are specified in the given list of IDs. (Default behavior: no
                        restrictions; include all IDs)

General File/Directory Configuration Options:
  -p PEOPLEFILE, --peoplefile PEOPLEFILE
                        JSON config file containing list of scheduled people/entities (in format: [[ID1, NAME1, ICS_FEED_URL1, TIME_ZONE1],
                        [ID2, NAME2...], ...]). (Default: ./ionical_monitor_list.json)
  -d DIRECTORY, --directory DIRECTORY
                        Directory where .ics files are stored. (Default: ./)

Changelog Options (only applicable if -l argument also given):
  -n NUM_LOOKBACKS, --num_lookbacks NUM_LOOKBACKS
                        Number of past schedule versions (per person) to compare. [Only used when displaying changelogs with -l flag.] (Default
                        behavior: 2 'lookbacks')

CSV Options (ALPHA/EXPERIMENTAL). Only applicable if -c specified:
  -t CSV_CONVERSION_FILE, --csv_conversion_file CSV_CONVERSION_FILE
                        JSON file w/ dictionary of conversion terms. [Only used when generating CSV via -c flag.] (Default:
                        ./ionical_csv_conversions.json)


     **********************************************************************

        NOTE: .ics filenames will/should have format 123__20200314.ics
             where 123 is an identifier corresponding to a particular
             person/entity and 20200314 is the date file was generated.

     **********************************************************************
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

