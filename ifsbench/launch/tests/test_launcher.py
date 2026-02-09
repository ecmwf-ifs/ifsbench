# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Launcher` implementations
"""


import pytest

from ifsbench import (
    BashLauncher,
    CompositeLauncher,
    DDTLauncher,
    DirectLauncher,
    Launcher,
    LauncherWrapper,
    MpirunLauncher,
    SerialisationMixin,
    SrunLauncher,
)


def build_config(
    base_launcher: Launcher,
    wrappers: list[LauncherWrapper],
) -> dict[str, SerialisationMixin]:
    composite = CompositeLauncher(base_launcher=base_launcher, wrappers=wrappers)
    return composite.dump_config()


@pytest.mark.parametrize(
    "base_launcher_type,base_executable,base_launcher_flags,wrappers_with_flags,ref_launcher",
    [
        (
            SrunLauncher,
            None,
            [],
            [],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[],
            ),
        ),
        (
            SrunLauncher,
            None,
            [],
            [
                (DDTLauncher, []),
            ],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[DDTLauncher()],
            ),
        ),
        (
            DirectLauncher,
            None,
            [],
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(),
                wrappers=[],
            ),
        ),
        (
            DirectLauncher,
            "mpirun",
            [],
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable="mpirun"),
                wrappers=[],
            ),
        ),
        (
            DirectLauncher,
            "mpirun",
            [],
            [(BashLauncher, [])],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable="mpirun"),
                wrappers=[BashLauncher()],
            ),
        ),
        (
            MpirunLauncher,
            None,
            ["--launcher-flags", "--flag"],
            [(DDTLauncher, []), (BashLauncher, [])],
            CompositeLauncher(
                base_launcher=MpirunLauncher(flags=["--launcher-flags", "--flag"]),
                wrappers=[DDTLauncher(), BashLauncher()],
            ),
        ),
        (
            SrunLauncher,
            None,
            [],
            [
                (
                    DDTLauncher,
                    [
                        "--ddt-option=5",
                    ],
                ),
            ],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[DDTLauncher(flags=["--ddt-option=5"])],
            ),
        ),
    ],
)
def test_composite_launcher(
    base_launcher_type,
    base_executable,
    base_launcher_flags,
    wrappers_with_flags,
    ref_launcher,
):
    base_launcher_config = {
        "flags": base_launcher_flags,
    }
    if base_executable:
        base_launcher_config["executable"] = base_executable

    print(f"base_launcher_config:\n{base_launcher_config}")
    base_launcher = base_launcher_type.from_config(base_launcher_config)
    print(f"base_launcher:\n{base_launcher.dump_config()}")
    wrappers = []
    for wrap in wrappers_with_flags:
        wrappers.append(wrap[0](flags=wrap[1]))
    config = build_config(base_launcher, wrappers)

    print(f"config:\n{config}")

    launcher = CompositeLauncher.from_config(config)

    assert launcher == ref_launcher
