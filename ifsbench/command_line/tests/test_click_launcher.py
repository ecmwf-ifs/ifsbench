# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Launcher` implementations
"""

from typing import List

import click
from click.testing import CliRunner
import pytest
import yaml

from ifsbench.command_line.click_launcher import LauncherBuilder, launcher_options

from ifsbench import (
    Arch,
    BashLauncher,
    CompositeLauncher,
    DDTLauncher,
    DirectLauncher,
    Launcher,
    MpirunLauncher,
    SrunLauncher,
)


def cli_test(tmp_path, cmd_flags):
    yaml_path = tmp_path / 'result.yaml'

    @click.command('click_test')
    @launcher_options
    def test_command(launcher_builder):
        with yaml_path.open('w', encoding='utf-8') as f:
            yaml.dump(launcher_builder.dump_config(), stream=f, encoding='utf-8')

    runner = CliRunner()
    result = runner.invoke(test_command, cmd_flags, standalone_mode=False)

    if hasattr(result, 'output_bytes'):
        print(result.output_bytes)
    else:
        print(result.stdout_bytes, result.stderr_bytes)

    if result.exception:
        raise result.exception

    assert result.exit_code == 0

    with yaml_path.open('r', encoding='utf-8') as f:
        builder = LauncherBuilder.from_config(yaml.safe_load(f))

    return builder


@pytest.mark.parametrize(
    'flags_in,default_launcher,default_launcher_flags,ref_launcher',
    [
        (
            [],
            SrunLauncher(),
            [],
            SrunLauncher(),
        ),
        (
            ['--launcher-flags', '--flagA', '-f', '--flagB'],
            MpirunLauncher(),
            [],
            MpirunLauncher(flags=['--flagA', '--flagB']),
        ),
        (
            [
                '--launcher-flags',
                '--flagA',
                '-f',
                '--flagB',
            ],
            DirectLauncher(executable='mpirun'),
            ['--default_flagA', '--default_flagB'],
            DirectLauncher(
                executable='mpirun',
                flags=['--default_flagA', '--default_flagB', '--flagA', '--flagB'],
            ),
        ),
    ],
)
def test_launcher_builder_from_default(
    tmp_path,
    flags_in,
    default_launcher,
    default_launcher_flags,
    ref_launcher,
):

    builder = cli_test(tmp_path, flags_in)

    launcher = builder.build_launcher(
        default_launcher=default_launcher, default_launcher_flags=default_launcher_flags
    )

    assert launcher == ref_launcher


@pytest.mark.parametrize(
    'config_in, flags_in,default_launcher,default_launcher_flags,ref_launcher',
    [
        (
            {
                'class_name': 'MpirunLauncher',
            },
            [],
            SrunLauncher(),
            ['--ignore_default_flagA', '--ignored_default_flagB'],
            MpirunLauncher(),
        ),
        (
            {'class_name': 'DirectLauncher', 'executable': 'mpirun'},
            [],
            None,
            [],
            DirectLauncher(executable='mpirun'),
        ),
        (
            {'class_name': 'MpirunLauncher', 'flags': ['--mpiflagA', '--mpiflagB']},
            ['-f', '--add_cli_flagA', '-f', '--add_cli_flagB'],
            SrunLauncher(),
            ['--ignore_default_flagA', '--ignored_default_flagB'],
            MpirunLauncher(
                flags=['--mpiflagA', '--mpiflagB', '--add_cli_flagA', '--add_cli_flagB']
            ),
        ),
        (
            {
                'class_name': 'CompositeLauncher',
                'base_launcher': {
                    'class_name': 'MpirunLauncher',
                    'flags': ['--mpiflagA', '--mpiflagB'],
                },
                'wrappers': [
                    {
                        'class_name': 'DDTLauncher',
                        'flags': [
                            '--ddtflagA',
                        ],
                    },
                    {'class_name': 'BashLauncher'},
                ],
            },
            [],
            None,
            [],
            CompositeLauncher(
                base_launcher=MpirunLauncher(flags=['--mpiflagA', '--mpiflagB']),
                wrappers=[DDTLauncher(flags=['--ddtflagA']), BashLauncher()],
            ),
        ),
        (
            {
                'class_name': 'MpirunLauncher',
                'flags': ['--config_flagA', '--config_flagB'],
            },
            ['-f', '--add_flagA', '--launcher-flags', '--add_flagB'],
            SrunLauncher(),
            [],
            MpirunLauncher(
                flags=['--config_flagA', '--config_flagB', '--add_flagA', '--add_flagB']
            ),
        ),
        (
            {
                'class_name': 'CompositeLauncher',
                'base_launcher': {
                    'class_name': 'MpirunLauncher',
                    'flags': ['--mpiflagA', '--mpiflagB'],
                },
                'wrappers': [
                    {
                        'class_name': 'DDTLauncher',
                        'flags': [
                            '--ddtflagA',
                        ],
                    },
                    {'class_name': 'BashLauncher'},
                ],
            },
            ['--launcher-flags', 'cli_flagA', '--launcher-flags', 'cli_flagB'],
            None,
            [],
            CompositeLauncher(
                base_launcher=MpirunLauncher(flags=['--mpiflagA', '--mpiflagB']),
                wrappers=[DDTLauncher(flags=['--ddtflagA']), BashLauncher()],
                flags=['cli_flagA', 'cli_flagB'],
            ),
        ),
    ],
)
def test_launcher_builder_from_config(
    tmp_path,
    config_in,
    flags_in,
    default_launcher,
    default_launcher_flags,
    ref_launcher,
):

    config_path = tmp_path / 'launcher.yml'
    flags_in.extend(['--launcher-config', config_path])

    builder = cli_test(tmp_path, flags_in)

    with config_path.open('w', encoding='utf-8') as f:
        yaml.dump(config_in, f)

    launcher = builder.build_launcher(
        default_launcher=default_launcher, default_launcher_flags=default_launcher_flags
    )

    assert launcher == ref_launcher


class DummyArch(Arch):
    def get_default_launcher(self) -> Launcher:
        return SrunLauncher(flags=['--ini_flagA', '--ini_flagB'])

    def get_default_launcher_flags(self) -> List[str]:
        return ['--default_flagA', '--default_flagB']

    def get_cpu_configuration(self):
        pass

    def process_job(self, job, **kwargs):
        pass


def test_build_from_arch():

    launcher = LauncherBuilder().build_from_arch(DummyArch())

    assert launcher == SrunLauncher(
        flags=['--ini_flagA', '--ini_flagB', '--default_flagA', '--default_flagB']
    )


def test_build_from_arch_adds_flags(tmp_path):

    flags_in = [
        '-f',
        '--cli_flagA',
    ]

    builder = cli_test(tmp_path, flags_in)
    launcher = builder.build_from_arch(DummyArch())

    assert launcher == SrunLauncher(
        flags=[
            '--ini_flagA',
            '--ini_flagB',
            '--default_flagA',
            '--default_flagB',
            '--cli_flagA',
        ]
    )


def test_build_from_arch_noarch_uses_flags(tmp_path):

    config_in = {
        'class_name': 'MpirunLauncher',
    }
    flags_in = [
        '-f',
        '--cli_flagA',
    ]
    config_path = tmp_path / 'launcher.yml'
    flags_in.extend(['--launcher-config', config_path])
    with config_path.open('w', encoding='utf-8') as f:
        yaml.dump(config_in, f)

    builder = cli_test(tmp_path, flags_in)

    launcher = builder.build_from_arch()

    assert launcher == MpirunLauncher(
        flags=[
            '--cli_flagA',
        ]
    )
