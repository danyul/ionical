import toml
from pathlib import Path

from ionical.ionical import main, sub_cfg, Cal

base_dir = "./"
test_dir = base_dir + "tests/"
test_sched_dir = test_dir + "ics_dir_test/"
exp_output_dir = test_dir + "expected_output/"
test_config_dir = test_dir + "config_test/"
cfg_fn = "test_ionical_config.toml"

cfg_path = Path(test_config_dir) / cfg_fn

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = toml.loads(f.read())
cal_tuples = [
    (k, v["description"], v["url"], v["tz"])
    for k, v in cfg["calendars"].items()
]
fmt_options = cfg["formatting"]

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
        summary_filters=["IHS"],
        cfg=cfg,
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
        summary_filters=["IHS"],
        cfg=cfg,
        # fmt_options=fmt_options,
    )
    out, err = capsys.readouterr()
    assert out == Path(exp_output_dir + "gilliam_schedule_1.txt").read_text()


def test_generate_csv(tmpdir):
    main(
        cals_data=cal_tuples,
        ics_dir=test_sched_dir,
        csv_export_file=Path(tmpdir) / "tmpcsv.csv",
        summary_filters=["IHS"],
        cfg=cfg,
    )
    csv = (Path(tmpdir) / "tmpcsv.csv").read_text()
    assert csv == Path(exp_output_dir + "full_monty.csv").read_text()
