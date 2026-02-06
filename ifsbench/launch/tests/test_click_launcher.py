# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Arch` implementations
"""

from pathlib import Path

import click
from click.testing import CliRunner
import pytest
import yaml

from ifsbench.launch.click_launcher import LauncherBuilder, launcher_options

from ifsbench import (
    BashLauncher,
    CompositeLauncher,
    DDTLauncher,
    DirectLauncher,
    MpirunLauncher,
    SrunLauncher,
)


def cli_test(cmd_flags):
    yaml_path = Path("result.yaml")

    @click.command("click_test")
    @launcher_options
    def test_command(launcher_builder):
        with yaml_path.open("w", encoding="utf-8") as f:
            yaml.dump(launcher_builder.dump_config(), stream=f, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(test_command, cmd_flags, standalone_mode=False)

    if hasattr(result, "output_bytes"):
        print(result.output_bytes)
    else:
        print(result.stdout_bytes, result.stderr_bytes)

    if result.exception:
        raise result.exception

    assert result.exit_code == 0

    with yaml_path.open("r", encoding="utf-8") as f:
        builder = LauncherBuilder.from_config(yaml.safe_load(f))

    return builder


@pytest.mark.parametrize(
    "flags_in,default_launcher,default_launcher_flags,ref_launcher,ref_flags",
    [
        (
            [],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[],
            ),
            [],
        ),
        (
            ["--debug-ddt"],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[DDTLauncher()],
            ),
            [],
        ),
        (
            ["--launcher-direct", ""],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(),
                wrappers=[],
            ),
            [],
        ),
        (
            ["--launcher-direct", "mpirun"],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable="mpirun"),
                wrappers=[],
            ),
            [],
        ),
        (
            ["--launcher-direct", "mpirun", "--bash"],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable="mpirun"),
                wrappers=[BashLauncher()],
            ),
            [],
        ),
        (["--debug-ddt", "--bash"], None, ["--flag"], None, []),
        (
            ["--debug-ddt", "--bash", "--launcher-flags", "--flag"],
            MpirunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=MpirunLauncher(),
                wrappers=[DDTLauncher(), BashLauncher()],
            ),
            [],
        ),
        (
            ["--launcher-mpirun", "--replace-launcher-flags"],
            SrunLauncher(),
            ["--something"],
            CompositeLauncher(
                base_launcher=MpirunLauncher(),
                wrappers=[],
            ),
            [],
        ),
        (
            ["--launcher-mpirun", "--add-launcher-flags"],
            SrunLauncher(),
            ["--something"],
            CompositeLauncher(
                base_launcher=MpirunLauncher(),
                wrappers=[],
            ),
            ["--something"],
        ),
        (
            ["--debug-launcher-flags", "--ddt-option=5"],
            SrunLauncher(),
            [],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[],
            ),
            [],
        ),
    ],
)
def test_launcher_builder_from_launcher(
    flags_in, default_launcher, default_launcher_flags, ref_launcher, ref_flags
):

    builder = cli_test(flags_in)

    launcher, flags = builder.build_launcher(
        default_launcher=default_launcher, default_launcher_flags=default_launcher_flags
    )

    assert launcher == ref_launcher
    assert flags == ref_flags
