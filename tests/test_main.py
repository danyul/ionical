import json
import os
import sys
from pathlib import Path


import pytest

base_dir = "./"

from ionical.ionical import main

# CONVERSION_TABLE = {
#     "PM: IHS Continuity Clinic": "C",
#     "AM: IHS Continuity Clinic": "C",
#     "AM: 8:30 IHS Continuity Clinic": "CL",
#     "PM: IHS Continuity Clinic IPCS": "CI",
#     "Pediatric Outpatient Clinic-IHS": "RP",
# }

test_dir = base_dir + "tests/"
test_sched_dir = test_dir + "ics_dir_test/"
exp_output_dir = test_dir + "expected_output/"
test_config_dir = test_dir + "config_test/"


with open(test_config_dir + "people.json", "r", encoding="utf-8") as f:
    people_tuples = json.loads(f.read())


def test_1984_not_here_yet():
    assert 2 + 2 != 5


def test_display_changelog(capsys):
    main(
        people_data=people_tuples,
        ics_dir=test_sched_dir,
        show_changelog=True,
        filters=["IHS"],
        change_report_record_template="  {label:10}{name:18}{start_str:19} "
        + "{summary:30}   [compare ver: {compare_date}]\n",
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "changelog_1.txt").read_text()


def test_display_schedule(capsys):
    main(
        people_data=people_tuples,
        ics_dir=test_sched_dir,
        show_schedule=True,
        people_filter=["Gilliam, Terry"],
        filters=["IHS"],
        shift_str_template = "Shift: {:11}",
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "gilliam_schedule_1.txt").read_text()


# def test_generate_csv(tmpdir):
#     main(
#         people_data=people_tuples,
#         ics_dir=test_sched_dir,
#         csv_file=Path(tmpdir) / "tmpcsv.csv",
#         filters=["IHS"],
#         include_empty_dates=True,
#         conversion_table=CONVERSION_TABLE,
#     )
#     csv = (Path(tmpdir) / "tmpcsv.csv").read_text()
#     assert csv == Path(exp_output_dir + "full_monty.csv").read_text()
