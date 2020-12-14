import toml
from pathlib import Path

from ionical.ionical import main, Cal

from ionical.__main__ import (
    cals_from_cfg,
    cfg_from_cfg_file,
)

base_dir = "./"
test_dir = base_dir + "tests/"
test_sched_dir = test_dir + "ics_dir_test/"
exp_output_dir = test_dir + "expected_output/"
test_config_dir = test_dir + "config_test/"
cfg_fn = "test_ionical_config.toml"

cal_tuples = cals_from_cfg(test_config_dir, cfg_fn)
cfg_options = cfg_from_cfg_file(test_config_dir, cfg_fn)
fmt_options = cfg_options["formatting"]

test_cfg_fn_path = Path(test_config_dir) / cfg_fn

with open(Path(test_cfg_fn_path), "r", encoding="utf-8") as f:
    csv_conversion_dict = toml.loads(f.read())["csv"]["substitutions"]


def test_1984_not_here_yet():
    assert 2 + 2 != 5


def test_display_changelog(capsys):
    main(
        cals_data=cal_tuples,
        ics_dir=test_sched_dir,
        show_changelog=True,
        filters=["IHS"],
        cfg=cfg_options,
        # fmt_options=fmt_options,
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "changelog_1.txt").read_text()


def test_display_schedule(capsys):
    main(
        cals_data=cal_tuples,
        ics_dir=test_sched_dir,
        show_schedule=True,
        cals_filter=["Gilliam, Terry"],
        filters=["IHS"],
        cfg=cfg_options,
        # fmt_options=fmt_options,
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "gilliam_schedule_1.txt").read_text()


def test_generate_csv(tmpdir):
    # all_cals = [
    #     Cal.from_tuple(cal_tuple=cal_tuple, ics_dir=test_sched_dir)
    #     for cal_tuple in cals_data
    # ]
    # writer = ScheduleWriter(
    #     cals=all_cals,
    #     filters=["IHS"],
    # )
    # writer.csv_write(
    #     conversion_table=csv_conversion_dict,
    #     csv_file=Path(tmpdir) / "tmpcsv.csv",
    #     include_empty_dates=True,
    #     fmt_options=fmt_options,
    # )
    main(
        cals_data=cal_tuples,
        ics_dir=test_sched_dir,
        csv_export_file=Path(tmpdir) / "tmpcsv.csv",
        filters=["IHS"],
        cfg=cfg_options,
    )
    csv = (Path(tmpdir) / "tmpcsv.csv").read_text()
    assert csv == Path(exp_output_dir + "full_monty.csv").read_text()
