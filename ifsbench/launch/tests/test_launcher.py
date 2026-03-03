# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`CompositeLauncher` implementations
"""

import datetime
from typing import Dict, List

import pytest

from ifsbench import (
    Job,
    BashLauncher,
    CompositeLauncher,
    DDTLauncher,
    DefaultEnvPipeline,
    DirectLauncher,
    EnvHandler,
    EnvOperation,
    Launcher,
    LauncherWrapper,
    MpirunLauncher,
    SerialisationMixin,
    SrunLauncher,
)


@pytest.fixture(name='test_env')
def fixture_test_env():
    return DefaultEnvPipeline(
        handlers=[
            EnvHandler(mode=EnvOperation.SET, key='SOME_VALUE', value='5'),
            EnvHandler(mode=EnvOperation.SET, key='OTHER_VALUE', value='6'),
            EnvHandler(mode=EnvOperation.DELETE, key='SOME_VALUE'),
        ]
    )


@pytest.fixture(name='test_env_none')
def fixture_test_env_none():
    return None


@pytest.fixture(name='test_now')
def fixture_test_now(monkeypatch):
    NOW_TIME = datetime.datetime(2026, 2, 9, 15, 57, 10)

    class DatetimeMock(datetime.datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            del args, kwargs
            return NOW_TIME

    monkeypatch.setattr(datetime, 'datetime', DatetimeMock)


def build_config(
    base_launcher: Launcher,
    wrappers: List[LauncherWrapper],
) -> Dict[str, SerialisationMixin]:
    composite = CompositeLauncher(base_launcher=base_launcher, wrappers=wrappers)
    return composite.dump_config()


@pytest.mark.parametrize(
    'base_launcher_type,base_executable,base_launcher_flags,wrappers_with_flags,ref_launcher',
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
            'mpirun',
            [],
            [],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable='mpirun'),
                wrappers=[],
            ),
        ),
        (
            DirectLauncher,
            'mpirun',
            [],
            [(BashLauncher, [])],
            CompositeLauncher(
                base_launcher=DirectLauncher(executable='mpirun'),
                wrappers=[BashLauncher()],
            ),
        ),
        (
            MpirunLauncher,
            None,
            ['--launcher-flags', '--flag'],
            [(DDTLauncher, []), (BashLauncher, [])],
            CompositeLauncher(
                base_launcher=MpirunLauncher(flags=['--launcher-flags', '--flag']),
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
                        '--ddt-option=5',
                    ],
                ),
            ],
            CompositeLauncher(
                base_launcher=SrunLauncher(),
                wrappers=[DDTLauncher(flags=['--ddt-option=5'])],
            ),
        ),
    ],
)
def test_composite_launcher_from_config(
    base_launcher_type,
    base_executable,
    base_launcher_flags,
    wrappers_with_flags,
    ref_launcher,
):
    base_launcher_config = {
        'flags': base_launcher_flags,
    }
    if base_executable:
        base_launcher_config['executable'] = base_executable

    print(f'base_launcher_config:\n{base_launcher_config}')
    base_launcher = base_launcher_type.from_config(base_launcher_config)
    print(f'base_launcher:\n{base_launcher.dump_config()}')
    wrappers = []
    for wrap in wrappers_with_flags:
        wrappers.append(wrap[0](flags=wrap[1]))
    config = build_config(base_launcher, wrappers)

    print(f'config:\n{config}')

    launcher = CompositeLauncher.from_config(config)

    assert launcher == ref_launcher


@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher(), MpirunLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
def test_compositelauncher_wrap_ddt_bash(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    base_launcher,
    base_launcher_flags,
    request,
):
    """
    Test the cmd component of the LaunchData object that is returned by
    CompositeLauncher.prepare with BashLauncher wrapper.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)
    request.getfixturevalue('test_now')

    launcher = CompositeLauncher(
        flags=base_launcher_flags,
        base_launcher=base_launcher,
        wrappers=[
            DDTLauncher(),
            BashLauncher(),
        ],
    )

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=[],
    )

    # Reference outputs per wrap
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=[],
    )

    ddt_data = DDTLauncher().wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    bash_data = BashLauncher().wrap(
        launch_data=ddt_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    assert result == bash_data
