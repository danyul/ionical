from pathlib import Path

from ionical.ionical import main

from ionical.__main__ import (
    cals_from_cfg,
    fmt_options_from_cfg,
)

base_dir = "./"
test_dir = base_dir + "tests/"
test_sched_dir = test_dir + "ics_dir_test/"
exp_output_dir = test_dir + "expected_output/"
test_config_dir = test_dir + "config_test/"

people_tuples = cals_from_cfg(test_config_dir, "test_ionical_config.toml")
fmt_options = fmt_options_from_cfg(test_config_dir, "test_ionical_config.toml")


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


# CONVERSION_TABLE = {
#     "PM: IHS Continuity Clinic": "C",
#     "AM: IHS Continuity Clinic": "C",
#     "AM: 8:30 IHS Continuity Clinic": "CL",
#     "PM: IHS Continuity Clinic IPCS": "CI",
#     "Pediatric Outpatient Clinic-IHS": "RP",
# }

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
