# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Arch` implementations
"""

import pytest

from ifsbench import Job, DirectLauncher, EnvHandler, EnvOperation, DefaultEnvPipeline


@pytest.fixture(name="test_env")
def fixture_test_env():
    return DefaultEnvPipeline(
        handlers=[
            EnvHandler(mode=EnvOperation.SET, key="SOME_VALUE", value="5"),
            EnvHandler(mode=EnvOperation.SET, key="OTHER_VALUE", value="6"),
            EnvHandler(mode=EnvOperation.DELETE, key="SOME_VALUE"),
        ]
    )


@pytest.fixture(name="test_env_none")
def fixture_test_env_none():
    return None


@pytest.mark.parametrize("executable", [None, "", "mpirun"])
@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [None, [], ["--cuda"]])
def test_directlauncher_run_dir(
    tmp_path,
    executable,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    request,
):
    """
    Test the run_dir component of the LaunchData object that is returned by
    DirectLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = DirectLauncher(executable=executable)

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags,
    )

    assert result.run_dir == tmp_path


@pytest.mark.parametrize("executable", [None, "", "mpirun"])
@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [None, [], ["--cuda"]])
def test_directlauncher_env(
    tmp_path,
    executable,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    request,
):
    """
    Test the env component of the LaunchData object that is returned by
    DirectLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    if env_pipeline:
        ref_pipeline = env_pipeline.copy(deep=True)
    else:
        ref_pipeline = DefaultEnvPipeline()

    if library_paths:
        for path in library_paths:
            ref_pipeline.add(
                EnvHandler(mode=EnvOperation.APPEND, key="LD_LIBRARY_PATH", value=path)
            )

    launcher = DirectLauncher(executable=executable)

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags,
    )

    assert result.env == ref_pipeline.execute()


@pytest.mark.parametrize("executable", [None, "", "mpirun"])
@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [None, [], ["--cuda"]])
def test_directlauncher_cmd(
    tmp_path,
    executable,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    request,
):
    """
    Test the cmd component of the LaunchData object that is returned by
    DirectLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = DirectLauncher(executable=executable)

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags,
    )

    ref_command = []

    if executable:
        ref_command.append(executable)

    if custom_flags:
        ref_command += custom_flags

    ref_command += cmd

    assert ref_command == result.cmd
