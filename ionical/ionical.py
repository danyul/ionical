"""Multipurpose ics util - changelogs, CSVs, schedule viewing."""
import csv
import re
import sys
import urllib.request
from collections import OrderedDict, defaultdict
from datetime import date, datetime, time, timedelta  # , tzinfo
from pathlib import Path
from typing import DefaultDict, Dict, List, NamedTuple, Optional
from typing import Set, Tuple
from textwrap import dedent

import icalendar  # type: ignore

import pytz

import recurring_ical_events  # type: ignore


DEF_ICS_DIR = "./"

DEF_TIME_FMT = "%H:%M:%S"
DEF_DATE_FMT = "%Y-%m-%d"
DEF_TIME_GROUP_FMT = ""
DEF_SUMMARY_LINE = "Start: {:12}   Time: {:12} {}  {}"

CHANGELOG_DEF_DATE_FMT = "%b %d, %Y"
CHANGELOG_DEF_TIME_FMT = " %I%p"
CHANGELOG_DEF_TIME_REPLACEMENTS = {" 0": " ", "AM": "am", "PM": "pm"}
DEF_CHANGE_REPORT_FMT = (
    " {label:8} {name:17} {start_str} {summary}  [comp {compare_date}]\n"
)

DEF_START_TIME_CAT_DICT = {
    "shift": {
        "All-Day": False,
        "AM": [[0, 12]],
        "PM": [[12, 24]],
    }
}


class Cal:
    """Cal (or entity) with a schedule specified via .ics format."""

    def __init__(
        self,
        cal_id: str,
        name: str,
        feed_url: Optional[str] = None,
        ics_dir: Optional[str] = DEF_ICS_DIR,
        timezone=None,
    ):
        self.cal_id = cal_id
        self.name = name
        self.ics_dir = ics_dir
        self.timezone = timezone
        if feed_url is not None:
            self.schedule_feed: Optional[ScheduleFeed] = ScheduleFeed(
                cal=self, url=feed_url
            )
        else:
            self.schedule_feed = None
        self._schedule_history = None

    def download_latest_schedule_version(self):
        assert self.ics_dir is not None, f"No ics_dir specified for {self}."
        assert self.schedule_feed is not None, f"No schedule_feed for {self}."
        self.schedule_feed.download_latest_schedule_version(
            ics_dir=self.ics_dir
        )
        # TODO: for performance, probably no need to get a whole new
        #       ScheduleHistory (Can instead just add the newly downloaded
        #       schedule to existing schedule history, if available)
        self._schedule_history = None  # clear cache to force new load

    @property
    def schedule_history(self):
        assert self.ics_dir is not None, f"No ics_dir specified for {self}."
        if self._schedule_history is None:
            self._schedule_history = ScheduleHistory.from_files_for_cal(
                cal=self,
                ics_dir=self.ics_dir,
            )
        return self._schedule_history

    @classmethod
    def from_tuple(cls, cal_tuple, ics_dir=DEF_ICS_DIR):
        id_, name, url, timezone = cal_tuple
        timezone = None if timezone == "" else timezone
        return cls(
            cal_id=id_,
            name=name,
            feed_url=url,
            ics_dir=ics_dir,
            timezone=timezone,
        )

    def current_schedule_and_version_date(self) -> Tuple["Schedule", date]:
        try:
            d, ical = self.schedule_history.most_recent_version_date_and_ical()
        except IndexError:
            print(
                dedent(
                    f"""\
               
               Uh oh!  Could not find .ics file for the calendar "{self.name}".\n
               Are you specifying the correct directory for your ics files? 
               (command line option -d)?\n
               Did you download the latest ics files (option -g)?\n
               For help, type 'ionical -h'. Quitting."""
                )
            )
            sys.exit(1)
        schedule = Schedule.from_icalendar(ical, self)
        return schedule, d

    @property
    def current_schedule(self) -> "Schedule":
        schedule, _ = self.current_schedule_and_version_date()
        return schedule

    def __str__(self):
        return f"{self.name} ({self.cal_id})"


# TODO More flexible implementation to allow user-specification
#      of what should be monitored for changes.
# TODO Better handle offset-naive vis-a-vis offset-aware dts.
class MonitoredEventData:
    """Data to be monitored for changes.

    ics files read by the icalendar and
    recurreng_ical_events packages  produce
    both datetime.date and datetime.datetime
    objects.  Those objects get stored within MonitoredEventData
    objects *as they were generated* by the icalendar package.
    """

    def __init__(self, event_date_or_datetime, summary, cal):
        self._date_or_datetime = event_date_or_datetime
        self._summary = summary
        self.cal = cal

    def __eq__(self, other) -> bool:
        return all(
            (
                isinstance(other, MonitoredEventData),
                self._date_or_datetime == other._date_or_datetime,
                self.cal.cal_id == other.cal.cal_id,
                self._summary == other._summary,
            )
        )

    def __hash__(self):
        return hash((self._date_or_datetime, self._summary, self.cal.cal_id))

    @property
    def date_or_datetime(self) -> date:
        return self._date_or_datetime

    @property
    def forced_date(self) -> date:
        if isinstance(self._date_or_datetime, datetime):
            return self._date_or_datetime.date()
        else:  # it must be a datettime.date
            return self._date_or_datetime

    @property
    def forced_datetime(self) -> datetime:
        if isinstance(self._date_or_datetime, datetime):
            return self._date_or_datetime
        else:  # it must be a datettime.date
            return datetime.combine(
                self._date_or_datetime, datetime.min.time()
            )

    @property
    def time(self) -> Optional[time]:
        if isinstance(self._date_or_datetime, datetime):
            return self._date_or_datetime.time()
        else:  # it must be a datetime.date, so there's no time
            return None

    @property
    def local_time(self):
        tz = pytz.timezone(self.cal.timezone)
        if isinstance(self._date_or_datetime, datetime):
            local_datetime = self._date_or_datetime.astimezone(tz)
            return local_datetime.time()
        else:
            return None

    @property
    def summary(self):
        return self._summary

    def start_time_cats(self, cat_class) -> Dict[str, str]:
        start_time_cats = {}
        for cat_type, cat_rules in cat_class.items():
            default_group_if_not_specified = "No Group Default Specified"
            default_group = default_group_if_not_specified
            start_time_cats[cat_type] = default_group
            # print(cat_rules)
            for cat, ranges_list in cat_rules.items():

                if ranges_list == "missing":
                    if not self.time:  # TODO: Make sure no falsy error
                        start_time_cats[cat_type] = cat
                        break
                    continue
                if ranges_list == "default":
                    default_group = cat
                    break
                for _range in ranges_list:
                    if not self.local_time:
                        break
                    start_time = self.local_time
                    lower_bound_in_hours, upper_bound_in_hours = _range
                    lower_bound_in_mins = lower_bound_in_hours * 60
                    upper_bound_in_mins = upper_bound_in_hours * 60
                    event_time_in_mins = (
                        start_time.hour * 60 + start_time.minute
                    )
                    if (lower_bound_in_mins <= event_time_in_mins) and (
                        event_time_in_mins < upper_bound_in_mins
                    ):
                        start_time_cats[cat_type] = cat
                        break  # not great, because should really break out of 2 loops
            if (
                default_group != default_group_if_not_specified
                and start_time_cats[cat_type] == default_group_if_not_specified
            ):
                start_time_cats[cat_type] = default_group

        return start_time_cats

    def display(self, fmt_cfg=None, classification_rules=None):
        if fmt_cfg is None:
            fmt_cfg = {}
        date_fmt = sub_cfg(fmt_cfg, "date_fmt", DEF_DATE_FMT)
        time_fmt = sub_cfg(fmt_cfg, "time_fmt", DEF_TIME_FMT)
        time_replacements = sub_cfg(fmt_cfg, "time_replacements", None)
        schedule_summary_line = sub_cfg(fmt_cfg, "event_summary", None)
        grouping_field = sub_cfg(fmt_cfg, "time_group", None)
        shift_str_template = sub_cfg(fmt_cfg, "time_group_fmt", None)
        start_time_cat_dict = sub_cfg(
            classification_rules, "by_start_time", DEF_START_TIME_CAT_DICT
        )

        if schedule_summary_line is None:
            schedule_summary_line = DEF_SUMMARY_LINE

        date_str = self.forced_date.strftime(date_fmt)
        time_str = (
            self.local_time.strftime(time_fmt) if self.local_time else ""
        )

        if time_replacements is not None:
            for pre, post in time_replacements.items():
                time_str = time_str.replace(pre, post)

        if shift_str_template is None:
            shift_str_template = DEF_TIME_GROUP_FMT
        shift_str = shift_str_template.format(
            self.start_time_cats(start_time_cat_dict)[grouping_field]
        )

        return schedule_summary_line.format(
            date_str,
            time_str,
            shift_str,
            self.summary,
        )

    def __str__(self):
        return self.display()


class Schedule:
    """Contain a set of MonitoredEventData objects."""

    def __init__(self, cal: Cal):
        self.events: Set[MonitoredEventData] = set()
        self.cal: Cal = cal

    @classmethod
    def from_icalendar(
        cls,
        icalCal: icalendar.cal.Calendar,
        cal: Cal,
        extra_timedelta_days_for_repeating_events: int = 1,
    ) -> "Schedule":
        """Initialize a schedule from an .ics file (icalCal).

        This is the primary way a Schedule object will be
        created in this package.

        Because the icalendar package will only return the
        first occurence in a repeating event, need to also obtain
        a set of event data using the recurring_ics_events package,
        and combine the two sets.
        """

        new_instance: Schedule = cls(cal=cal)

        kerr_count = 0
        events_by_icalendar_lookup: Set[MonitoredEventData] = set()
        for ical_event in icalCal.subcomponents:
            try:
                med: MonitoredEventData = MonitoredEventData(
                    event_date_or_datetime=ical_event["DTSTART"].dt,
                    summary=ical_event["SUMMARY"],
                    cal=new_instance.cal,
                )
                events_by_icalendar_lookup.add(med)
            except KeyError:
                # ignore timezone from ics file (maybe implement later?)
                if not isinstance(ical_event, icalendar.cal.Timezone):
                    kerr_count = kerr_count + 1

        # TODO KeyError may represent difficulty reading Google Calendar
        # ics format's iniital TIMEZONE section in ics file.  For at least
        # one test case, removing that section solved the
        # sole encountered KeyError.
        if kerr_count > 0:
            msg = (
                f"{kerr_count} non-TimeZone KeyErrors encountered reading ical"
                + f' for "{cal.cal_id}".\n'
            )
            sys.stderr.write(msg)

        # Get the earliest and laetst dates that are explicitly specified in
        # the ics file (ie, not specified by recurrence).
        # These will be used when querying for recurrent events.
        min_date = min(
            [x.forced_date for x in events_by_icalendar_lookup],
            default=None,
        )
        max_date = max(
            [x.forced_date for x in events_by_icalendar_lookup],
            default=None,
        )
        # Search for recurrent events that occur a specified # of days
        # beyond the latest explicitly-stated event date.
        if min_date is None and max_date is None:
            new_instance.events = events_by_icalendar_lookup
            return new_instance

        if min_date is None or max_date is None:
            raise ValueError(f"Problem: min_date={min_date}, max_date={max_date}")

        max_date += timedelta(days=extra_timedelta_days_for_repeating_events)

        events_by_RIE_lookup: Set[MonitoredEventData] = {
            MonitoredEventData(
                event_date_or_datetime=ical_event["DTSTART"].dt,
                summary=ical_event["SUMMARY"],
                cal=new_instance.cal,
            )
            for ical_event in recurring_ical_events.of(icalCal).between(
                (min_date.year, min_date.month, min_date.day),
                (max_date.year, max_date.month, max_date.day),
            )
        }

        merged_events: Set[MonitoredEventData] = (
            events_by_RIE_lookup | events_by_icalendar_lookup
        )
        new_instance.events = merged_events
        return new_instance

    def filtered_events(
        self,
        earliest_date: date = None,
        latest_date: date = None,
        summary_filters: Optional[List[str]] = None,
    ) -> List[MonitoredEventData]:
        """Get MonitoredEventData objects filtered by summary and date."""

        def meets_filter_criteria(event: MonitoredEventData) -> bool:
            return not any(
                (
                    summary_filters
                    and not any(f in event.summary for f in summary_filters),
                    earliest_date and event.forced_date < earliest_date,
                    latest_date and event.forced_date > latest_date,
                )
            )

        if summary_filters is None:
            summary_filters = []
        return [
            event
            for event in sorted(
                self.events, key=lambda x: (x.forced_date, x.summary)
            )
            if meets_filter_criteria(event)
        ]

    def display(
        self,
        earliest_date: date = None,
        latest_date: date = None,
        summary_filters: Optional[List[str]] = None,
        version_date: Optional[date] = None,
        fmt_cfg=None,
        classification_rules=None,
    ) -> str:
        if summary_filters is None:
            summary_filters = []
        tz = pytz.timezone(self.cal.timezone)
        header = f"\n\nSchedule for {self.cal.name} ({tz})"
        if version_date:
            header += f" [version {version_date}]:"
        header += "\n\n"
        body = "\n".join(
            [
                event.display(fmt_cfg, classification_rules)
                for event in self.filtered_events(
                    earliest_date=earliest_date,
                    latest_date=latest_date,
                    summary_filters=summary_filters,
                )
            ]
        )
        return header + body

    def __str__(self):
        return self.display()


class ScheduleFeed:
    """Holder for a Cal's .ics URL."""

    downloaded_ics_default_filename_pattern = re.compile(
        r"""
        ^(?P<cal_id>.*)            # cal_id at the start (any string)
        __                         # double _ delimiter
        (?P<ymd>                   # to capture concatenated year/month/day
        (?P<year>[0-9]{4})         # 4 digit year
        (?P<month>[0-9]{2})        # 2 digit month
        (?P<day>[0-9]{2})          # 2 digit day of month
        )                          # end capturing of <ymd>
        \.ics                      # suffix
    """,
        re.VERBOSE,
    )

    def __init__(self, cal: Cal, url: str):
        self.cal = cal
        self.url = url

    def ics_filename_for_today(self):
        f = f"{self.cal.cal_id}__{date.today().strftime('%Y%m%d')}.ics"
        return f

    def download_latest_schedule_version(self, ics_dir) -> None:
        """Save the current .ics file version of the Cal's schedule."""

        with urllib.request.urlopen(self.url) as ics_http_response:
            ics_text = ics_http_response.read().decode()

        with open(
            file=Path(ics_dir) / self.ics_filename_for_today(),
            mode="w",
            encoding="utf-8",
            newline="",
        ) as ics_file:
            ics_file.write(ics_text)


# TODO: consider making SC full class
# if we do that, then switch to direct reference to Cal object
#   (rather than indirect lookup via Cal.cal_id)
#   ? Pros vs Cons ?
class ScheduleChange(NamedTuple):
    """Data to be displayed on a change log report."""

    reference_date: date
    comparison_date: date
    cal_id: str
    event_summary: str
    event_start: datetime  # TODO: ???? clarify naive/local/aware issues
    change_type: str  # either "a" for addition, or "r" for removal


class ScheduleHistory:
    """Container for multiple versions of .ics file data."""

    def __init__(self, cal):
        self.cal: Cal = cal
        self.sched_versions_by_date: OrderedDict[
            date, icalendar.cal.Calendar
        ] = OrderedDict([])

    @classmethod
    def from_files_for_cal(
        cls, cal: Cal, ics_dir, file_pat=None
    ) -> "ScheduleHistory":
        """Instantiate by reading in .ics files for a Cal.

        Determination of which ics files correspond to
        Cal is made by matching Cal.cal_id to
        the id embedded in the filenames, as specified
        by the regex found in ScheduleFeed class.
        """

        if file_pat is None:
            file_pat = ScheduleFeed.downloaded_ics_default_filename_pattern
        new_hx = cls(cal)
        d = Path(ics_dir)
        files_matches = [
            (f, file_pat.match(f.name))
            for f in d.iterdir()
            if (
                file_pat.match(f.name)
                and file_pat.match(f.name).group("cal_id") == str(cal.cal_id)
            )
        ]
        for f, m in sorted(files_matches, key=lambda x: (x[1].group("ymd"))):
            yr, mo, day = m.group("year"), m.group("month"), m.group("day")
            vers_date = date(int(yr), int(mo), int(day))
            new_hx.sched_versions_by_date[vers_date] = cls.get_icalendar_cal(f)
        return new_hx

    def get_changes_for_date(self, version_date) -> List[ScheduleChange]:
        """Get a cal's schedule changes for a given date.

        Get the ScheduleChanges for the Cal referenced by
        this ScheduleHistory object, comparing the version
        of calendar events for the date given in the
        parameter version_date with the next older schedule
        for that cal.
        """

        i = list(self.sched_versions_by_date.keys()).index(version_date)
        ref_date, ref_vers = list(self.sched_versions_by_date.items())[i]
        comp_date, comp_vers = list(self.sched_versions_by_date.items())[i - 1]

        reference_schedule = Schedule.from_icalendar(
            icalCal=ref_vers,
            cal=self.cal,
        )
        comparison_schedule = Schedule.from_icalendar(
            icalCal=comp_vers,
            cal=self.cal,
        )

        additions = reference_schedule.events - comparison_schedule.events
        removals = comparison_schedule.events - reference_schedule.events

        pid = self.cal.cal_id
        a = [
            ScheduleChange(
                ref_date, comp_date, pid, x.summary, x.forced_datetime, "a"
            )
            for x in additions
        ]
        r = [
            ScheduleChange(
                ref_date, comp_date, pid, x.summary, x.forced_datetime, "r"
            )
            for x in removals
        ]
        return a + r

    # TODO: consider directly referencing Cal object from ScheduleChange?
    #   (rather than indirect lookup via Cal.cal_id)
    def change_log(
        self, num_changelogs=None
    ) -> Dict[date, List[ScheduleChange]]:
        """Get a list of ScheduleChanges from multiple version dates.

        Compare each schedule version with the immediately preceding
        version (except for the very oldest version, for which there
        will be nothing available for comparison.)  For each schedule
        version date, provide a list of the changes.
        """
        length = len(list(self.sched_versions_by_date))
        if num_changelogs is None:
            change_slice = slice(1, length)
        else:
            change_slice = slice(max(1, length - num_changelogs), length)
        return {
            date_: self.get_changes_for_date(date_)
            for date_ in list(self.sched_versions_by_date.keys())[change_slice]
        }

    # TODO implement user option for which versions to analyze?
    # TODO allow user to specify sorting/grouping
    # TODO consider putting in its own class
    @classmethod
    def change_log_report_for_cals(
        cls,
        cals: List[Cal],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        summary_filters: Optional[List[str]] = None,
        num_changelogs=None,
        changelog_action_dict=None,
        fmt_cfg=None,
    ) -> str:
        """Return a filtered/sorted list of changes.

        Return a history of changes for multiple
        dates/cals, filtering events by a user-specifiable
        list of search terms (matched to an event's
        summary field), and a user-specifiable date
        range.

        If no filters are provided, then
        no search filter is applied.
        """
        # fmt_cfg = {} if fmt_cfg is None else fmt_cfg
        date_fmt = sub_cfg(fmt_cfg, "date_fmt", CHANGELOG_DEF_DATE_FMT)
        time_fmt = sub_cfg(fmt_cfg, "time_fmt", CHANGELOG_DEF_TIME_FMT)
        time_replacements = sub_cfg(
            fmt_cfg, "time_replacement", CHANGELOG_DEF_TIME_REPLACEMENTS
        )
        change_report_record_template = sub_cfg(
            fmt_cfg, "change_report", DEF_CHANGE_REPORT_FMT
        )

        def cal_by_id(cal_id: str) -> Cal:
            for p in cals:
                if p.cal_id == cal_id:
                    return p
            raise KeyError(f"Did not find id {cal_id}.")

        def meets_filter_criteria(c: ScheduleChange) -> bool:
            return not any(
                (
                    summary_filters
                    and not any(f in c.event_summary for f in summary_filters),
                    earliest_date and c.event_start.date() < earliest_date,
                    latest_date and c.event_start.date() > latest_date,
                )
            )

        def local_format_dt(
            datetime_: datetime,
            cal: Cal,
            date_fmt: str = CHANGELOG_DEF_DATE_FMT,
            time_fmt=CHANGELOG_DEF_TIME_FMT,
            time_replacements=None,
        ) -> str:

            if time_replacements is None:
                time_replacements = CHANGELOG_DEF_TIME_REPLACEMENTS

            tz_datetime = datetime_.astimezone(pytz.timezone(cal.timezone))

            date_str = tz_datetime.date().strftime(date_fmt)
            time_str = tz_datetime.time().strftime(time_fmt)
            if time_replacements is not None:
                for pre, post in time_replacements.items():
                    time_str = time_str.replace(pre, post)

            return date_str + time_str

        if summary_filters is None:
            summary_filters = []
        if changelog_action_dict is None:
            changelog_action_dict = {"a": "ADD:", "r": "REMOVE:"}

        changes_by_ver_date: DefaultDict[
            date, List[ScheduleChange]
        ] = defaultdict(list)

        for p in cals:
            for date_, changes in p.schedule_history.change_log(
                num_changelogs=num_changelogs,
            ).items():
                changes_by_ver_date[date_] = changes_by_ver_date[date_] + (
                    [c for c in changes if meets_filter_criteria(c)]
                )
        report = "\n"  # ""

        cbvd = sorted(changes_by_ver_date.items(), key=lambda x: x[0])
        for version_date, changes in cbvd:
            report += f"\n\nUpdates for sched vers dated {str(version_date)}:"
            if len(changes) == 0:
                report += " NO CHANGES"
            report += "\n\n"
            for c in sorted(
                changes,
                key=lambda x: (
                    x.event_start.year,
                    x.event_start.month,
                    x.event_start.day,
                    cal_by_id(x.cal_id).name,
                    x.event_summary,
                ),
            ):
                cal = cal_by_id(c.cal_id)
                event_start_str = local_format_dt(
                    datetime_=c.event_start,
                    cal=cal,
                    date_fmt=date_fmt,
                    time_fmt=time_fmt,
                    time_replacements=time_replacements,
                )

                report += change_report_record_template.format(
                    name=cal.name,
                    label=changelog_action_dict[c.change_type],
                    start_str=event_start_str,
                    summary=c.event_summary,
                    compare_date=c.comparison_date,
                )

        return report

    def most_recent_version_date_and_ical(
        self,
    ) -> Tuple[date, icalendar.cal.Calendar]:
        """Return most recent available schedule version/version date."""
        last_version_index = len(self.sched_versions_by_date) - 1
        return list(self.sched_versions_by_date.items())[last_version_index]

    @classmethod
    def get_icalendar_cal(cls, filepathname) -> icalendar.cal.Calendar:
        with open(filepathname, "r", encoding="utf-8") as file_:
            c = icalendar.Calendar.from_ical(file_.read())
        return c


class ScheduleWriter:
    def __init__(
        self,
        cals: List[Cal],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        summary_filters: Optional[List[str]] = None,
    ):
        self.summary_filters = summary_filters
        self.cals = cals

        self.events_by_cal_id: Dict[str, List[MonitoredEventData]] = {
            cal.cal_id: cal.current_schedule.filtered_events(
                earliest_date=earliest_date,
                latest_date=latest_date,
                summary_filters=summary_filters,
            )
            for cal in cals
        }

        event_dates = [
            event.forced_date
            for cal_id, events in self.events_by_cal_id.items()
            for event in events
        ]

        self.earliest_date = (
            earliest_date if earliest_date else min(event_dates)
        )
        self.latest_date = latest_date if latest_date else max(event_dates)

    def csv_write(
        self,
        csv_file,
        csv_dialect: str = "excel",
        include_empty_dates: bool = False,
        conversion_table: Dict[str, str] = None,
        classification_rules=None,
        csv_cfg=None,
    ):

        start_time_cat_dict = sub_cfg(
            classification_rules, "by_start_time", None
        )  # DEF_START_TIME_CAT_DICT
        if start_time_cat_dict is None:
            print("Quitting- can't find by_start_time confg info.\n")
            sys.exit(1)

        # https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
        def daterange(start_date, end_date):
            for n in range(int((end_date - start_date).days)):
                yield start_date + timedelta(n)

        conversion_table = {} if conversion_table is None else conversion_table

        def convert_if_lookup_found(summary):
            return (
                conversion_table[summary]
                if summary in conversion_table
                else summary
            )

        cat_type = sub_cfg(csv_cfg, "grouping")
        if cat_type is None:
            print("Quitting- can't find grouping confg info.\n")
            sys.exit(1)

        all_day_field_name = sub_cfg(csv_cfg, "all_day_category", None)
        plists_by_date = OrderedDict([])
        for date_ in daterange(self.earliest_date, self.latest_date):
            plist = list("" for _ in range(len(self.cals)))
            for cal in self.cals:
                events = self.events_by_cal_id[cal.cal_id]
                index_ = self.cals.index(cal)
                cat_range_names = start_time_cat_dict[
                    cat_type
                ].keys()  # csv_cfg["output"][ "order" ]
                event_date_groups = {}
                for range_name in cat_range_names:
                    event_date_groups[range_name] = next(
                        (
                            x
                            for x in events
                            if x.forced_date == date_
                            and x.start_time_cats(start_time_cat_dict)[
                                cat_type
                            ]
                            == range_name
                        ),
                        None,
                    )
                shown_options = sub_cfg(csv_cfg, "order")
                if shown_options is None:
                    print("Quitting- can't find 'order' confg info.\n")
                    sys.exit(1)
                csv_exp_str = sub_cfg(csv_cfg, "format")
                if csv_exp_str is None:
                    print("Quitting- can't find 'format' confg info.\n")
                    sys.exit(1)
                not_found_str = sub_cfg(csv_cfg, "text_if_not_present", "None")

                text = (
                    csv_exp_str.format(
                        *[
                            convert_if_lookup_found(
                                event_date_groups[c].summary  # type: ignore
                            )
                            if event_date_groups[c]
                            else not_found_str
                            for c in shown_options
                        ]
                    )
                    if any([event_date_groups[c] for c in shown_options])
                    else ""
                )

                # below hack addresses scenario when all-day events need to fill in other shifts
                all_day_spec_case = sub_cfg(
                    csv_cfg, "all_day_behavior_workaround", False
                )
                if all_day_spec_case:
                    if all_day_field_name is None:
                        print(
                            "You opted for the all-day "
                            "workaround but no all-day category found in config."
                        )
                        all_day_spec_case = False
                if all_day_spec_case and event_date_groups[all_day_field_name]:
                    if not any([event_date_groups[c] for c in shown_options]):
                        special_event = convert_if_lookup_found(
                            event_date_groups[all_day_field_name].summary  # type: ignore
                        )
                        text = csv_exp_str.format(
                            *([special_event] * len(shown_options))
                        )
                    else:
                        text = csv_exp_str.format(
                            *[
                                convert_if_lookup_found(
                                    event_date_groups[c].summary  # type: ignore
                                )
                                if event_date_groups[c]
                                else convert_if_lookup_found(
                                    event_date_groups[  # type: ignore
                                        all_day_field_name
                                    ].summary
                                )
                                for c in shown_options
                            ]
                        )

                plist[index_] = text

            if set(plist) != {""} or include_empty_dates:
                plists_by_date[date_] = plist

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect=csv_dialect)
            writer.writerow([""] + [p.cal_id for p in self.cals])
            for date_, plist in plists_by_date.items():
                writer.writerow([date_] + plist)


def sub_cfg(
    cfg: Optional[Dict],
    sub_key: str,
    default_val=None,
    noisy: bool = False,
    success_msg: str = "Located config sub_key: {0}.  Value: {1}.",
    no_sub_key_msg: str = "Could not locate config sub_key '{0}'."
    "Setting {0} to default value: {1}.",
    no_cfg_msg: str = "No config dict to seek sub_key '{0}'."
    "Setting {0} to default value: {1}.",
):
    if cfg is None:
        if noisy:
            print(no_cfg_msg.format(sub_key, default_val))
        return default_val
    else:
        try:
            if noisy:
                print(success_msg.format(sub_key, cfg[sub_key]))
            return cfg[sub_key]
        except KeyError:
            if noisy:
                print(no_sub_key_msg.format(sub_key, default_val))
            return default_val


def main(
    cals_data: List[Tuple[str, str, str, str]],
    cals_filter: Optional[List[str]] = None,
    ics_dir=DEF_ICS_DIR,
    download_option: bool = False,
    show_schedule: bool = False,
    show_changelog: bool = False,
    csv_export_file: str = None,
    earliest_date: Optional[date] = None,
    latest_date: Optional[date] = None,
    summary_filters: Optional[List[str]] = None,
    num_changelogs=None,  # (for changelogs)
    cfg=None,
    verbose=0,
) -> None:

    output = ""

    classification_rules = sub_cfg(cfg, "event_classifications")
    fmt_cfg = sub_cfg(cfg, "formatting")

    all_cals = [
        Cal.from_tuple(cal_tuple=cal_tuple, ics_dir=ics_dir)
        for cal_tuple in cals_data
    ]

    if cals_filter:
        chosen_cals = [p for p in all_cals if p.cal_id in cals_filter]
    else:
        chosen_cals = all_cals

    if download_option:
        for p in chosen_cals:
            p.download_latest_schedule_version()

    if show_changelog:
        report = ScheduleHistory.change_log_report_for_cals(
            cals=chosen_cals,
            earliest_date=earliest_date,
            latest_date=latest_date,
            summary_filters=summary_filters,
            num_changelogs=num_changelogs,
            fmt_cfg=sub_cfg(fmt_cfg, "changelog"),
        )
        output += report

    if show_schedule:
        for cal in chosen_cals:
            schedule, version_date = cal.current_schedule_and_version_date()
            schedule_display = schedule.display(
                earliest_date=earliest_date,
                latest_date=latest_date,
                summary_filters=summary_filters,
                version_date=version_date,
                fmt_cfg=sub_cfg(fmt_cfg, "schedule_view"),
                classification_rules=classification_rules,
            )
            output += schedule_display

    if csv_export_file:
        csv_cfg = sub_cfg(cfg, "csv")
        csv_substitutions = sub_cfg(csv_cfg, "substitutions", {})
        writer = ScheduleWriter(
            cals=chosen_cals,
            earliest_date=earliest_date,
            latest_date=latest_date,
            summary_filters=summary_filters,
        )
        empty = sub_cfg(csv_cfg, "include_empty_dates", verbose, False)
        writer.csv_write(
            conversion_table=csv_substitutions,
            csv_file=csv_export_file,
            include_empty_dates=empty,
            classification_rules=classification_rules,
            csv_cfg=csv_cfg,
        )

    print(output, end="")
