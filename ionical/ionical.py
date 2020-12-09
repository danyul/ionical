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

import icalendar  # type: ignore

import pytz

import recurring_ical_events  # type: ignore


DEF_ICS_DIR = "./ics/"

# TODO: Timezone config management
# TODO: Include sample people.json file in manifest (or whatever necessary)

# TODO: will want to rename/refactor to "ScheduledEntity" or somesuch
#       - since it doesn't really need to be a person. "Schedulee"?
class Person:
    """Person (or entity) with a schedule specified via .ics format."""

    def __init__(
        self,
        person_id: str,
        name: str,
        feed_url: Optional[str] = None,
        ics_dir: Optional[str] = DEF_ICS_DIR,
        timezone=None,
    ):
        self.person_id = person_id
        self.name = name
        self.ics_dir = ics_dir
        self.timezone = timezone
        if feed_url is not None:
            self.schedule_feed: Optional[ScheduleFeed] = ScheduleFeed(
                person=self, url=feed_url
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
            self._schedule_history = ScheduleHistory.from_files_for_person(
                person=self,
                ics_dir=self.ics_dir,
            )
        return self._schedule_history

    @classmethod
    def from_tuple(cls, person_tuple, ics_dir=DEF_ICS_DIR):
        id_, name, url, timezone = person_tuple
        timezone = None if timezone == "" else timezone
        return cls(
            person_id=id_,
            name=name,
            feed_url=url,
            ics_dir=ics_dir,
            timezone=timezone,
        )

    def current_schedule_and_version_date(self) -> Tuple["Schedule", date]:
        d, ical = self.schedule_history.most_recent_version_date_and_ical()
        schedule = Schedule.from_icalendar(ical, self)
        return schedule, d

    @property
    def current_schedule(self) -> "Schedule":
        schedule, _ = self.current_schedule_and_version_date()
        return schedule

    def __str__(self):
        return f"{self.name} ({self.person_id})"


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

    def __init__(self, event_date_or_datetime, summary, person):
        self._date_or_datetime = event_date_or_datetime
        self._summary = summary
        self.person = person

    def __eq__(self, other) -> bool:
        return all(
            (
                isinstance(other, MonitoredEventData),
                self._date_or_datetime == other._date_or_datetime,
                self.person.person_id == other.person.person_id,
                self._summary == other._summary,
            )
        )

    def __hash__(self):
        return hash(
            (self._date_or_datetime, self._summary, self.person.person_id)
        )

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
        tz = pytz.timezone(self.person.timezone)
        if isinstance(self._date_or_datetime, datetime):
            local_datetime = self._date_or_datetime.astimezone(tz)
            return local_datetime.time()
        else:
            return None

    @property
    def summary(self):
        return self._summary

    # TODO: CORRECT FOR TIMEZONES
    # TODO: CORRECT THIS UGLY (AND COMPLETELY WRONG) HACK!!!!!
    #   (It does work for AM / PM IHS workshifts.)
    @property
    def workshift(self) -> str:  # am or pm or all-day
        if self.time:
            if self._date_or_datetime.time().hour > 18:
                return "PM"
            else:
                return "AM"
        else:
            return "All-Day"

    def display(
        self,
        date_fmt="%Y-%m-%d",
        time_fmt="%H:%M:%S",
        schedule_summary_line=None,
        shift_str_template=None,
        time_replacements=None,
        **kwargs,
    ):

        if schedule_summary_line is None:
            schedule_summary_line = "Start: {:12}   Time: {:12} {}  {}"

        date_str = self.forced_date.strftime(date_fmt)
        time_str = (
            self.local_time.strftime(time_fmt) if self.local_time else ""
        )

        if time_replacements is not None:
            for pre, post in time_replacements.items():
                time_str = time_str.replace(pre, post)

        if shift_str_template is None:
            shift_str_template = "Shift: {:11}"
        shift_str = shift_str_template.format(self.workshift)

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

    def __init__(self, person: Person):
        self.events: Set[MonitoredEventData] = set()
        self.person: Person = person

    @classmethod
    def from_icalendar(
        cls,
        cal: icalendar.cal.Calendar,
        person: Person,
        extra_timedelta_days_for_repeating_events: int = 1,
    ) -> "Schedule":
        """Initialize a schedule from an .ics file (cal).

        This is the primary way a Schedule object will be
        created in this package.

        Because the icalendar package will only return the
        first occurence in a repeating event, need to also obtain
        a set of event data using the recurring_ics_events package,
        and combine the two sets.
        """

        new_instance: Schedule = cls(person=person)

        kerr_count = 0
        events_by_icalendar_lookup: Set[MonitoredEventData] = set()
        for ical_event in cal.subcomponents:
            try:
                med: MonitoredEventData = MonitoredEventData(
                    event_date_or_datetime=ical_event["DTSTART"].dt,
                    summary=ical_event["SUMMARY"],
                    person=new_instance.person,
                )
                events_by_icalendar_lookup.add(med)
            except KeyError:
                kerr_count = kerr_count + 1
                continue

        #TODO KeyError may represent difficulty reading Google Calendar
        # ics format's iniital TIMEZONE section in ics file.  For at least
        # one test case, removing that section solved the 
        # sole encountered KeyError.
        if kerr_count > 0:
            msg = (
                f"{kerr_count} KeyErrors encountered while reading ical"
                + f" for {person.person_id}. Associated events disregarded."
            )
            sys.stderr.write(msg)

        # Get the earliest and laetst dates that are explicitly specified in
        # the ics file (ie, not specified by recurrence).
        # These will be used when querying for recurrent events.
        min_date = min([x.forced_date for x in events_by_icalendar_lookup])
        max_date = max([x.forced_date for x in events_by_icalendar_lookup])
        # Search for recurrent events that occur a specified # of days
        # beyond the latest explicitly-stated event date.
        max_date += timedelta(days=extra_timedelta_days_for_repeating_events)

        events_by_RIE_lookup: Set[MonitoredEventData] = {
            MonitoredEventData(
                event_date_or_datetime=ical_event["DTSTART"].dt,
                summary=ical_event["SUMMARY"],
                person=new_instance.person,
            )
            for ical_event in recurring_ical_events.of(cal).between(
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
        filters: Optional[List[str]] = None,
    ) -> List[MonitoredEventData]:
        """Get MonitoredEventData objects filtered by summary and date."""

        def meets_filter_criteria(event: MonitoredEventData) -> bool:
            return not any(
                (
                    filters and not any(f in event.summary for f in filters),
                    earliest_date and event.forced_date < earliest_date,
                    latest_date and event.forced_date > latest_date,
                )
            )

        if filters is None:
            filters = []
        return [
            event
            for event in sorted(
                self.events, key=lambda x: (x.forced_date, x.summary)
            )
            if meets_filter_criteria(event)
        ]

    # paramaters possibly passed via **kwargs
    # include: date_fmt, time_fmt, shift_str,
    # schedule_summary_line, time_replacements
    def display(
        self,
        earliest_date: date = None,
        latest_date: date = None,
        filters: Optional[List[str]] = None,
        version_date: Optional[date] = None,
        **kwargs,
    ) -> str:
        if filters is None:
            filters = []
        tz = pytz.timezone(self.person.timezone)
        header = f"\n\nSchedule for {self.person.name} ({tz})"
        if version_date:
            header += f" [version {version_date}]:"
        header += "\n\n"
        body = "\n".join(
            [
                event.display(**kwargs)
                for event in self.filtered_events(
                    earliest_date=earliest_date,
                    latest_date=latest_date,
                    filters=filters,
                )
            ]
        )
        return header + body

    def __str__(self):
        return self.display()


# TODO Def need to make more efficient, less ugly. Prob use more generators
class ScheduleWriter:
    def __init__(
        self,
        people: List[Person],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        filters: Optional[List[str]] = None,
    ):
        self.filters = filters
        self.people = people

        self.events_by_person_id: Dict[str, List[MonitoredEventData]] = {
            person.person_id: person.current_schedule.filtered_events(
                earliest_date=earliest_date,
                latest_date=latest_date,
                filters=filters,
            )
            for person in people
        }

        event_dates = [
            event.forced_date
            for person_id, events in self.events_by_person_id.items()
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
        **kwargs,
    ):

        # QUICK HACK TO GET IT WORKING - DON'T CRITICIZE!! :)
        # TODO: OBVIOUSLY MAKE GENERALIZABLE and dekludge/dehack
        # https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
        def daterange(start_date, end_date):
            for n in range(int((end_date - start_date).days)):
                yield start_date + timedelta(n)

        if conversion_table is None:
            conversion_table = {}

        def convert_if_lookup_found(summary):
            if summary in conversion_table:
                return conversion_table[summary]
            else:
                return summary

        # TODO: De-HACK!  (Dirty implementation-specific code, to be fixed)
        # DON'T CRITICIZE!
        plists_by_date = OrderedDict([])
        for date_ in daterange(self.earliest_date, self.latest_date):
            plist = list("" for _ in range(len(self.people)))
            for person in self.people:
                events = self.events_by_person_id[person.person_id]
                index_ = self.people.index(person)
                am_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "AM"
                    ),
                    None,
                )
                pm_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "PM"
                    ),
                    None,
                )
                all_day_shift = next(
                    (
                        x
                        for x in events
                        if x.forced_date == date_ and x.workshift == "All-Day"
                    ),
                    None,
                )
                text = ""
                if all_day_shift and all([am_shift, pm_shift]):
                    text = "ERROR"
                else:
                    if all_day_shift and not pm_shift:
                        pm_shift = all_day_shift
                    if all_day_shift and not am_shift:
                        am_shift = all_day_shift
                    if am_shift:
                        text = convert_if_lookup_found(am_shift.summary) + "-"
                    if pm_shift and not am_shift:
                        text = "X" + "-"
                    if pm_shift:
                        text += convert_if_lookup_found(pm_shift.summary)
                    if am_shift and not pm_shift:
                        text += "X"
                if am_shift:
                    text = convert_if_lookup_found(am_shift.summary) + "-"
                if pm_shift and not am_shift:
                    text = "O" + "-"
                if pm_shift:
                    text += convert_if_lookup_found(pm_shift.summary)
                if am_shift and not pm_shift:
                    text += "O"
                plist[index_] = text
            if set(plist) != {""} or include_empty_dates:
                plists_by_date[date_] = plist

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect=csv_dialect)
            writer.writerow([""] + [p.person_id for p in self.people])
            for date_, plist in plists_by_date.items():
                writer.writerow([date_] + plist)


class ScheduleFeed:
    """Holder for a Person's .ics URL."""

    downloaded_ics_default_filename_pattern = re.compile(
        r"""
        ^(?P<person_id>.*)         # person_id at the start (any string)
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

    def __init__(self, person: Person, url: str):
        self.person = person
        self.url = url

    def ics_filename_for_today(self):
        f = f"{self.person.person_id}__{date.today().strftime('%Y%m%d')}.ics"
        return f

    def download_latest_schedule_version(self, ics_dir) -> None:
        """Save the current .ics file version of the Person's schedule."""

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
# if we do that, then switch to direct reference to Person object
#   (rather than indirect lookup via Person.person_id)
#   ? Pros vs Cons ?
class ScheduleChange(NamedTuple):
    """Data to be displayed on a change log report."""

    reference_date: date
    comparison_date: date
    person_id: str
    event_summary: str
    event_start: datetime  # TODO: ???? clarify naive/local/aware issues
    change_type: str  # either "a" for addition, or "r" for removal


class ScheduleHistory:
    """Container for multiple versions of .ics file data."""

    def __init__(self, person):
        self.person: Person = person
        self.sched_versions_by_date: OrderedDict[
            date, icalendar.cal.Calendar
        ] = OrderedDict([])

    @classmethod
    def from_files_for_person(
        cls, person: Person, ics_dir, file_pat=None
    ) -> "ScheduleHistory":
        """Instantiate by reading in .ics files for a Person.

        Determination of which ics files correspond to
        Person is made by matching Person.person_id to
        the id embedded in the filenames, as specified
        by the regex found in ScheduleFeed class.
        """

        if file_pat is None:
            file_pat = ScheduleFeed.downloaded_ics_default_filename_pattern
        new_hx = cls(person)
        d = Path(ics_dir)
        files_matches = [
            (f, file_pat.match(f.name))
            for f in d.iterdir()
            if (
                file_pat.match(f.name)
                and file_pat.match(f.name).group("person_id")
                == str(person.person_id)
            )
        ]
        for f, m in sorted(files_matches, key=lambda x: (x[1].group("ymd"))):
            yr, mo, day = m.group("year"), m.group("month"), m.group("day")
            vers_date = date(int(yr), int(mo), int(day))
            new_hx.sched_versions_by_date[vers_date] = cls.get_icalendar_cal(f)
        return new_hx

    def get_changes_for_date(self, version_date) -> List[ScheduleChange]:
        """Get a person's schedule changes for a given date.

        Get the ScheduleChanges for the Person referenced by
        this ScheduleHistory object, comparing the version
        of calendar events for the date given in the
        parameter version_date with the next older schedule
        for that person.
        """

        i = list(self.sched_versions_by_date.keys()).index(version_date)
        ref_date, ref_vers = list(self.sched_versions_by_date.items())[i]
        comp_date, comp_vers = list(self.sched_versions_by_date.items())[i - 1]

        reference_schedule = Schedule.from_icalendar(
            cal=ref_vers,
            person=self.person,
        )
        comparison_schedule = Schedule.from_icalendar(
            cal=comp_vers,
            person=self.person,
        )

        additions = reference_schedule.events - comparison_schedule.events
        removals = comparison_schedule.events - reference_schedule.events

        pid = self.person.person_id
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

    # TODO: consider directly referencing Person object from ScheduleChange?
    #   (rather than indirect lookup via Person.person_id)
    def change_log(
        self, num_lookbacks=None
    ) -> Dict[date, List[ScheduleChange]]:
        """Get a list of ScheduleChanges from multiple version dates.

        Compare each schedule version with the immediately preceding
        version (except for the very oldest version, for which there
        will be nothing available for comparison.)  For each schedule
        version date, provide a list of the changes.
        """
        length = len(list(self.sched_versions_by_date))
        if num_lookbacks is None:
            change_slice = slice(1, length)
        else:
            change_slice = slice(max(1, length - num_lookbacks), length)
        return {
            date_: self.get_changes_for_date(date_)
            for date_ in list(self.sched_versions_by_date.keys())[change_slice]
        }

    # TODO implement user option for which versions to analyze?
    # TODO allow user to specify sorting/grouping
    # TODO consider putting in its own class
    @classmethod
    def change_log_report_for_people(
        cls,
        people: List[Person],
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None,
        filters: Optional[List[str]] = None,
        date_fmt=None,
        time_fmt=None,
        time_replacements=None,
        num_lookbacks=None,
        change_report_record_template=" {label:8} {name:17} {start_str}"
        + " {summary}  [comp {compare_date}]\n",
        changelog_action_dict=None,
        **kwargs,
    ) -> str:
        """Return a filtered/sorted list of changes.

        Return a history of changes for multiple
        dates/people, filtering events by a user-specifiable
        list of search terms (matched to an event's
        summary field), and a user-specifiable date
        range.

        If no filters are provided, then
        no search filter is applied.
        """

        def person_by_id(person_id: str) -> Person:
            for p in people:
                if p.person_id == person_id:
                    found_person = p
                    break
            return found_person

        def meets_filter_criteria(c: ScheduleChange) -> bool:
            if (
                (filters and not any(f in c.event_summary for f in filters))
                or (earliest_date and c.event_start.date() < earliest_date)
                or (latest_date and c.event_start.date() > latest_date)
            ):
                return False
            return True

        def local_format_dt(
            datetime_: datetime,
            person: Person,
            date_fmt: Optional[str] = None,
            time_fmt=None,
            time_replacements=None,
        ) -> str:
            if date_fmt is None:
                date_fmt = "%b %d, %Y"
            if time_fmt is None:
                time_fmt = " %I%p"
            if time_replacements is None:
                time_replacements = {" 0": " ", "AM": "am", "PM": "pm"}

            tz_datetime = datetime_.astimezone(pytz.timezone(person.timezone))

            date_str = tz_datetime.date().strftime(date_fmt)
            time_str = tz_datetime.time().strftime(time_fmt)
            if time_replacements is not None:
                for pre, post in time_replacements.items():
                    time_str = time_str.replace(pre, post)

            return date_str + time_str

        if filters is None:
            filters = []
        if changelog_action_dict is None:
            changelog_action_dict = {"a": "ADD:", "r": "REMOVE:"}

        changes_by_ver_date: DefaultDict[
            date, List[ScheduleChange]
        ] = defaultdict(list)

        for p in people:
            for date_, changes in p.schedule_history.change_log(
                num_lookbacks=num_lookbacks,
            ).items():
                changes_by_ver_date[date_] = changes_by_ver_date[date_] + (
                    [c for c in changes if meets_filter_criteria(c)]
                )
        report = "\n"

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
                    person_by_id(x.person_id).name,
                    x.event_summary,
                ),
            ):
                person = person_by_id(c.person_id)
                event_start_str = local_format_dt(
                    datetime_=c.event_start,
                    person=person,
                    date_fmt=date_fmt,
                    time_fmt=time_fmt,
                    time_replacements=time_replacements,
                )

                report += change_report_record_template.format(
                    name=person.name,
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


# Parameters optionally passed through as **kwargs:
#   date_fmt=None,  # (for showing changelogs or schedules)
#   time_fmt=None,  # (for showing changelogs or schedules)
#   time_replacements=None,  # (for showing changelogs or schedules)
#   shift_str_template=None,  # (for showing schedules)
#   schedule_summary_line=None,  # (for showing schedules)
#   include_empty_dates=False,  # (for CSV writing)
#   conversion_table=None,   # (for CSV writing)
def main(
    people_data: List[Tuple[str, str, str, str]],
    people_filter: Optional[List[str]] = None,
    ics_dir=DEF_ICS_DIR,
    download_option: bool = False,
    show_schedule: bool = False,
    show_changelog: bool = False,
    csv_file=None,
    earliest_date: Optional[date] = None,
    latest_date: Optional[date] = None,
    filters: Optional[List[str]] = None,
    num_lookbacks=None,  # (for changelogs)
    **kwargs,
) -> None:

    output = ""

    all_people = [
        Person.from_tuple(person_tuple=person_tuple, ics_dir=ics_dir)
        for person_tuple in people_data
    ]

    if people_filter:
        chosen_people = [p for p in all_people if p.person_id in people_filter]
    else:
        chosen_people = all_people

    if download_option:
        for p in chosen_people:
            p.download_latest_schedule_version()

    if show_changelog:
        report = ScheduleHistory.change_log_report_for_people(
            people=chosen_people,
            earliest_date=earliest_date,
            latest_date=latest_date,
            filters=filters,
            num_lookbacks=num_lookbacks,
            **kwargs,
        )
        # **kwargs to possibly include the parameters:
        #   date_fmt, time_fmt, time_replacements,
        output += report

    if csv_file:
        writer = ScheduleWriter(
            people=chosen_people,
            earliest_date=earliest_date,
            latest_date=latest_date,
            filters=filters,
        )
        writer.csv_write(csv_file=csv_file, **kwargs)
        # **kwargs to possibly include the parameters:
        #   include_empty_dates, conversion_table

    if show_schedule:
        for person in chosen_people:
            schedule, version_date = person.current_schedule_and_version_date()
            schedule_display = schedule.display(
                earliest_date=earliest_date,
                latest_date=latest_date,
                filters=filters,
                version_date=version_date,
                **kwargs,
            )
            # **kwargs to possibly include the parameters:
            # date_fmt, time_fmt, time_replacements,
            # shift_str_template, schedule_summary_line
            output += schedule_display

    print(output, end="")
