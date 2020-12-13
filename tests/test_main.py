import toml
from pathlib import Path

from ionical.ionical import main, Person

from ionical.__main__ import (
    cals_from_cfg,
    cfg_from_cfg_file,
)
from ionical.csv_export import ScheduleWriter

base_dir = "./"
test_dir = base_dir + "tests/"
test_sched_dir = test_dir + "ics_dir_test/"
exp_output_dir = test_dir + "expected_output/"
test_config_dir = test_dir + "config_test/"
cfg_fn = "test_ionical_config.toml"

people_tuples = cals_from_cfg(test_config_dir, cfg_fn)
fmt_options = cfg_from_cfg_file(test_config_dir, cfg_fn)["formatting"]

test_cfg_fn_path = Path(test_config_dir) / cfg_fn

with open(Path(test_cfg_fn_path), "r", encoding="utf-8") as f:
    csv_conversion_dict = toml.loads(f.read())["csv_substitutions"]

def test_1984_not_here_yet():
    assert 2 + 2 != 5


def test_display_changelog(capsys):
    main(
        people_data=people_tuples,
        ics_dir=test_sched_dir,
        show_changelog=True,
        filters=["IHS"],
        fmt_options=fmt_options,
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
        fmt_options=fmt_options,
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "gilliam_schedule_1.txt").read_text()


def test_generate_csv(tmpdir):
    all_cals = [
        Person.from_tuple(person_tuple=cal_tuple, ics_dir=test_sched_dir)
        for cal_tuple in people_tuples
    ]
    writer = ScheduleWriter(
        cals=all_cals,
        filters=["IHS"],
    )
    writer.csv_write(
        conversion_table=  csv_conversion_dict, 
        csv_file=Path(tmpdir) / "tmpcsv.csv",
        include_empty_dates=True,
        fmt_options=fmt_options,
    )
    csv = (Path(tmpdir) / "tmpcsv.csv").read_text()
    assert csv == Path(exp_output_dir + "full_monty.csv").read_text()


#     main(
#         people_data=people_tuples,
#         ics_dir=test_sched_dir,
#         csv_file=Path(tmpdir) / "tmpcsv.csv",
#         filters=["IHS"],
#         include_empty_dates=True,
#         conversion_table=CONVERSION_TABLE,
#     )