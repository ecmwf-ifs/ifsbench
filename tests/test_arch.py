# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Arch` implementations
"""

import re

import pytest

from conftest import Watcher
from ifsbench import logger, arch_registry


@pytest.fixture(name='watcher')
def fixture_watcher():
    """Return a :any:`Watcher` to check test output"""
    return Watcher(logger=logger, silent=True)


@pytest.mark.parametrize('arch,np,nt,hyperthread,expected', [
    ('atos_aa', 64, 4, 1, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--hint=nomultithread'
    ]),
    ('atos_aa', 256, 4, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--hint=nomultithread'
    ]),
    ('atos_aa', 256, 16, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=8',
        '--cpus-per-task=16', '--ntasks-per-core=1', '--hint=nomultithread'
    ]),
    ('atos_aa', 256, 16, 2, [
        'srun', '--ntasks=256', '--ntasks-per-node=16',
        '--cpus-per-task=16', '--ntasks-per-core=2', '--hint=multithread'
    ]),
])
def test_arch_run(watcher, arch, np, nt, hyperthread, expected):
    """
    Verify the launch command for certain architecture configurations
    looks as expected
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, dryrun=True)

    for string in expected:
        assert string in watcher.output

@pytest.mark.parametrize('arch,np,nt,hyperthread,gpus_per_task,expected,launch_script_expected', [
    ('atos_ac', 64, 4, 1, None, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--qos=np', '--hint=nomultithread'
    ], None),
    ('atos_ac', 64, 4, 1, 0, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--qos=np', '--hint=nomultithread'
    ], None),
    ('atos_ac', 64, 32, 1, 1, [
        'srun', '--ntasks=64', '--ntasks-per-node=4', '--qos=ng',
        '--cpus-per-task=32', '--ntasks-per-core=1', '--gres=gpu:4', '--hint=nomultithread',
        'select_gpu.sh'
    ], ['VISIBLE_DEVICES_PER_RANK=(1 0 3 2)', 'CUDA_VISIBLE_DEVICES=${VISIBLE_DEVICES_PER_RANK[${SLURM_LOCALID}]']),
    ('atos_ac', 64, 32, 1, 4, [
        'srun', '--ntasks=64', '--ntasks-per-node=1', '--qos=ng',
        '--cpus-per-task=32', '--ntasks-per-core=1', '--gres=gpu:4', '--hint=nomultithread',
        'select_gpu.sh'
    ], ['VISIBLE_DEVICES_PER_RANK=(1)', 'CUDA_VISIBLE_DEVICES=${VISIBLE_DEVICES_PER_RANK[${SLURM_LOCALID}]']),
    ('lumi_g', 256, 4, 1, None, [
        'srun', '--ntasks=256', '--ntasks-per-node=14', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ], None),
    ('lumi_g', 256, 4, 1, 0, [
        'srun', '--ntasks=256', '--ntasks-per-node=14', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ], None),
    ('lumi_g', 256, 4, 1, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=8', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gres=gpu:8'
    ], None),
    ('lumi_g', 256, 4, 1, 4, [
        'srun', '--ntasks=256', '--ntasks-per-node=2', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gres=gpu:8'
    ], None),
])
def test_arch_gpu_run(tmp_path, watcher, arch, np, nt, gpus_per_task, hyperthread, expected, launch_script_expected):
    """
    Verify the launch command for certain architecture configurations
    looks as expected
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, gpus_per_task=gpus_per_task, dryrun=True, cwd=tmp_path)

    for string in expected:
        assert string in watcher.output

    if launch_script_expected:
        assert (tmp_path/'select_gpu.sh').exists()
        assert tmp_path.stat().st_mode & 0o750
        launch_script = (tmp_path/'select_gpu.sh').read_text()
        for string in launch_script_expected:
            assert string in launch_script
    else:
        assert not (tmp_path/'select_gpu.sh').exists()


@pytest.mark.parametrize('np,nt,gpus_per_node,expected,launch_script_expected',[
    (
        64, 32, 4,
        ['--ntasks=64', '--ntasks-per-node=4', '--gres=gpu:4', '--hint=nomultithread', '/select_gpu.sh'],
        ['VISIBLE_DEVICES_PER_RANK=(1 0 3 2)', 'CUDA_VISIBLE_DEVICES=${VISIBLE_DEVICES_PER_RANK[${SLURM_LOCALID}]']
    ),
    (
        64, 8, 4,
        ['--ntasks=64', '--ntasks-per-node=16', '--gres=gpu:4', '--hint=nomultithread', '/select_gpu.sh'],
        [
            'VISIBLE_DEVICES_PER_RANK=(1 1 1 1 0 0 0 0 3 3 3 3 2 2 2 2)',
            'CUDA_VISIBLE_DEVICES=${VISIBLE_DEVICES_PER_RANK[${SLURM_LOCALID}]'
        ]
    ),
    (
        64, 17, 4,
        ['--ntasks=64', '--ntasks-per-node=7', '--gres=gpu:4', '--hint=nomultithread', '/select_gpu.sh'],
        [
            'VISIBLE_DEVICES_PER_RANK=(1 1,0 0 0,3 3 3,2 2)',
            'CUDA_VISIBLE_DEVICES=${VISIBLE_DEVICES_PER_RANK[${SLURM_LOCALID}]'
        ]
    )
])
def test_arch_gpu_run_atos_ac(tmp_path, watcher, np, nt, gpus_per_node, expected, launch_script_expected):
    """
    Custom test for Atos_ac to validate the GPU mapping when
    using gpus_per_node
    """
    obj = arch_registry['atos_ac']

    with watcher:
        obj.run('cmd', np, nt, 1, gpus_per_node=gpus_per_node, dryrun=True, cwd=tmp_path)

    for string in expected:
        assert string in watcher.output

    assert (tmp_path/'select_gpu.sh').exists()
    assert tmp_path.stat().st_mode & 0o750
    launch_script = (tmp_path/'select_gpu.sh').read_text()
    for string in launch_script_expected:
        assert string in launch_script


@pytest.mark.parametrize('arch,np,nt,hyperthread,gpus_per_task,user_options,order', [
    ('atos_ac', 64, 4, 1, 0, ['--qos=some_partition'], [
        '--qos=np', '--qos=some_partition'
    ]),
    ('atos_ac', 64, 4, 1, 1, ['--qos=first_partition', '--qos=second_partition'], [
        '--qos=ng', '--qos=first_partition', '--qos=second_partition'
    ]),
    ('lumi_g', 256, 4, 1, 2, ['--partition=lumi-c', '--gpus-per-task=0'], [
        '--partition=standard-g', '--partition=lumi-c', '--gpus-per-task=0'
    ]),
])
def test_arch_user_override(tmp_path, watcher, arch, np, nt, gpus_per_task, hyperthread,
    user_options, order):
    """
    Verify that the launch user options are added to the end of the launcher
    command (where they override previously set values).
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, gpus_per_task=gpus_per_task,
            launch_user_options=user_options, dryrun=True, cwd=tmp_path)

    # The order-list contains some launcher flags that must appear in this order
    # in the launch command. Check that all the values exist and that they are
    # in the given order.
    positions = []
    for string in order:
        assert string in watcher.output
        positions.append(watcher.output.find(string))

    assert positions == sorted(positions)


@pytest.mark.parametrize('arch,np,gpus_per_task,mpi_gpu_aware, env_expected', [
    ('atos_ac', 64, 0, True, {}),
    ('atos_ac', 64, 4, True, {}),
    ('atos_ac', 8, 0, False, {}),
    ('lumi_g', 64, 8, True, {
        'MPICH_GPU_SUPPORT_ENABLED': '1',
        'MPICH_SMP_SINGLE_COPY_MODE': 'NONE',
        'MPICH_GPU_IPC_ENABLED': '0'
    }),
    ('lumi_g', 64, 8, True, {}),
])
def test_arch_gpu_mpi_aware(tmp_path, watcher, arch, np, gpus_per_task, mpi_gpu_aware,
    env_expected):
    """
    Verify that setting mpi_gpu_aware sets the right environment flags (and
    that it doesn't crash).
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run(
            'cmd', np, 1, 1, gpus_per_task=gpus_per_task,
            mpi_gpu_aware=mpi_gpu_aware, dryrun=True, cwd=tmp_path
        )

    for key, value in env_expected.items():
        # Match anything of the form key: value in the watcher output. Keep in
        # mind that key or value might be surrounded by whitespaces or ' or ".
        regex = f"{key}['\" ]*:['\" ]*{value}"
        print(regex)
        print(watcher.output)
        assert re.search(regex, watcher.output) is not None
