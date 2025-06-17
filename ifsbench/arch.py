# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Architecture specifications
"""
from abc import ABC, abstractmethod
import os
from pathlib import Path

from .job import CpuConfiguration, CpuBinding, Job
from .launcher import Launcher, MpirunLauncher, SrunLauncher, AprunLauncher
from .logging import warning
from .util import as_tuple, execute


__all__ = ['Arch', 'Workstation', 'XC40Cray', 'XC40Intel', 'AtosAaIntel',
           'LumiC', 'LumiG', 'arch_registry']


class Arch(ABC):
    """
    Machine and compiler architecture on which to run the IFS

    This provides compiler and environment assumptions for MPI-parallel runs.

    An implementation of this class must be provided for each target system.
    It must declare the CPU configuration in :attr:`cpu_config` and the
    launcher in :attr:`launcher` that is used for MPI-parallel execution.

    For multiple toolchains/runtime environments on a single physical system
    it can be beneficial to create an intermediate class describing common
    properties (such as :attr:`cpu_config`) and derived classes to specify
    the bespoke configuration.
    """

    cpu_config: CpuConfiguration
    """The CPU configuration of the architecture

    This describes the available compute capability on each compute node
    from which the job resource requirements can be derived.
    """

    launcher: Launcher
    """The MPI launcher that is used on the architecture

    This is used to derive the relevant launch command to execute the application
    using the resource requirements specified in a run's :any:`Job` description.
    """

    @classmethod
    @abstractmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            **kwargs):
        """
        Arch-specific general purpose executable execution

        This method must be implemented by architecture-specific implementations,
        either to launch :data:`cmd` directly or to build a job specification
        :any:`Job` and launch this via :meth:`run_job`.

        Parameters
        ----------
        cmd : list or str
            The command of the MPI executable (without the launch command)
        tasks : int
            The total number of MPI tasks to use
        cpus_per_task : int
            The number of threads to start for each MPI task
        threads_per_core : int
            The number of hyperthreads to use on each core
        launch_cmd : list or str, optional
            User-provided launch command that is used instead of generating
            a launch command based on :data:`job` specifications
        launch_user_options : list or str, optional
            User-provided launch command options that are added to the
            generated launch command. Ignored if :data:`launch_cmd` is given.
        logfile : str or :any:`pathlib.Path`, optional
            An optional logfile to store the output
        env : dict, optional
            Custom environment to use
        gpus_per_task: int, optional
            The number of GPUs that are used per MPI task
        kwargs :
            Other arguments that may be used in the architecture implementation
            or may be passed on to :any:`execute`
        """

    @classmethod
    def run_job(cls, cmd, job, launch_cmd=None, launch_user_options=None,
                logfile=None, env=None, **kwargs):
        """
        Arch-specific general purpose executable execution for :any:`Job` specification

        This method can be used by the architecture-specific implementations.

        It launches :data:`cmd` using the resource requirements specified in :data:`job`.

        The architecture-specific :attr:`launcher` is used to generate the
        required launch command for that. The user can override this behaviour
        by providing a custom launch command in :data:`launch_cmd`.

        Parameters
        ----------
        cmd : list or str
            The command of the MPI executable (without the launch command)
        job : :any:`Job`
            The resource requirements of the job to be run
        launch_cmd : list or str, optional
            User-provided launch command that is used instead of generating
            a launch command based on :data:`job` specifications
        launch_user_options : list or str, optional
            User-provided launch command options that are added to the
            generated launch command. Ignored if :data:`launch_cmd` is given.
        logfile : str or :any:`pathlib.Path`, optional
            An optional logfile to store the output
        env : dict, optional
            Custom environment to use
        kwargs :
            Other arguments that may be used in the architecture implementation
            or may be passed on to :any:`execute`
        """
        assert isinstance(job, Job)
        assert job.cpu_config == cls.cpu_config

        # Just pop a few arguments from kwargs that are used by some
        # architectures but not by all. If we don't remove them here, they may
        # cause trouble inside the subsequent "execute" call.
        kwargs.pop('mpi_gpu_aware', False)

        if env is None:
            env = os.environ.copy()

        if launch_cmd is None:
            launch_cmd = as_tuple(cls.launcher.get_launch_cmd(job, user_options=launch_user_options))
        else:
            launch_cmd = as_tuple(launch_cmd)

        full_cmd = ' '.join(launch_cmd + as_tuple(cmd))
        execute(full_cmd, logfile=logfile, env=env, **kwargs)


class Workstation(Arch):
    """
    Default setup for ECMWF workstations.
    """

    class WorkstationCpuConfig(CpuConfiguration):
        """Most workstations have a quad-core CPU with hyperthreading"""

        sockets_per_node = 1
        cores_per_socket = 4
        threads_per_core = 2

    cpu_config = WorkstationCpuConfig

    launcher = MpirunLauncher

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            **kwargs):
        """Build job description using :attr:`cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        # TODO: Ensure proper pinning

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class XC40(Arch):
    """
    Hardware and launcher setup for ECMWF's Cray XC40 system

    Toolchain specific settings are provided in derived
    classes :class:`XC40Cray` and :class:`XC40Intel` for Cray compiler and
    Intel Compiler, respectively
    """

    class XC40CpuConfig(CpuConfiguration):
        """Dual-socket Intel Xeon E5-2650 v4 (12 cores/24 threads, 2.2 GHz)"""

        sockets_per_node = 2
        cores_per_socket = 12
        threads_per_core = 2

    cpu_config = XC40CpuConfig

    launcher = AprunLauncher


class XC40Cray(XC40):
    """
    Cray compiler-toolchain setup for :any:`XC40`
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            **kwargs):
        """Build job description using :attr:`XC40.cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task

        # Fill nodes without hyperthreading
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, cls.cpu_config.cores_per_node))
        tasks_per_socket = tasks_per_node // 2

        # Binding-strategy -cc cpu
        bind = CpuBinding.BIND_CORES

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  tasks_per_socket=tasks_per_socket, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core, bind=bind)

        # Strict memory containment
        if launch_user_options is None:
            launch_user_options = []
        launch_user_options += ['-ss']

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class XC40Intel(XC40):
    """
    Intel compiler-toolchain setup for :any:`XC40`
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            **kwargs):
        """Build job description using :attr:`XC40.cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        env['OMP_PLACES'] = 'threads'
        env['OMP_PROC_BIND'] = 'close'

        # Fill nodes without hyperthreading
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, cls.cpu_config.cores_per_node))
        tasks_per_socket = tasks_per_node // 2

        # Binding-strategy -cc depth
        bind = CpuBinding.BIND_THREADS

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  tasks_per_socket=tasks_per_socket, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core, bind=bind)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class Atos(Arch):
    """
    Hardware setup for ECMWF's aa system in Bologna
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            gpus_per_node=None, **kwargs):
        """Build job description using :attr:`cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        # TODO: Ensure proper pinning

        # Fill nodes as much as possible
        max_tasks_per_node = cls.cpu_config.cores_per_node * threads_per_core // cpus_per_task
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, max_tasks_per_node))

        launch_user_options = list(as_tuple(launch_user_options))

        # If GPUs are used, request the GPU partition.
        if gpus_per_task:
            if gpus_per_node is not None:
                warning((
                    f'Both, gpus_per_task={gpus_per_task} and gpus_per_node={gpus_per_node} specified, '
                    'ignoring gpus_per_task'
                ))
            else:
                tasks_per_node = min(
                    tasks_per_node,
                    cls.cpu_config.gpus_per_node // gpus_per_task
                )
                gpus_per_node = min(gpus_per_task * tasks_per_node, cls.cpu_config.gpus_per_node)

        if gpus_per_node:
            launch_user_options.insert(0, '--qos=ng')

            # To ensure we correctly bind GPUs to CPUs we write a little
            # wrapper script that maps the correct CUDA_VISIBLE_DEVICES
            # id to each rank locally per node.
            # Because the mapping from NUMA domain to GPU is
            # [1->0, 0->1, 3->2, 2->3], we need to apply some reordering here

            # The GPU that is closest to each core
            core_to_gpu_mapping = {core: 1 for core in range(32)} | {core: 0 for core in range(32, 64)}
            core_to_gpu_mapping |= {core: 3 for core in range(64, 96)} | {core: 2 for core in range(96, 128)}

            # Determine the cores that each task is using on a node
            physical_cpus_per_task = (cpus_per_task - 1) // threads_per_core + 1
            physical_cores_per_task = {
                local_rank: [physical_cpus_per_task * local_rank + i for i in range(physical_cpus_per_task)]
                for local_rank in range(tasks_per_node)
            }

            # The GPUs to be used by each rank
            task_gpu_strings = [
                ','.join(dict.fromkeys(
                    str(core_to_gpu_mapping[core])
                    for core in physical_cores_per_task[local_rank]
                ))
                for local_rank in range(tasks_per_node)
            ]
            wrapper_str = f"""
#!/bin/bash
VISIBLE_DEVICES_PER_RANK=({' '.join(task_gpu_strings)})
export CUDA_VISIBLE_DEVICES=${{VISIBLE_DEVICES_PER_RANK[${{SLURM_LOCALID}}]}}
exec $*
            """.strip()

            rundir = kwargs.get('cwd')
            if not rundir:
                raise RuntimeError('No rundir given to Atos.run')
            wrapper = Path(rundir/'select_gpu.sh')
            wrapper.write_text(wrapper_str, encoding='utf_8')
            wrapper.chmod(0o750)

            cmd = [str(wrapper), *cmd]
        elif tasks * cpus_per_task > 32:
            # By default, stuff on Atos runs on the GPIL nodes which allow only
            # up to 32 cores. If more resources are needed, the compute
            # partition should be requested.
            launch_user_options.insert(0, '--qos=np')


        # Bind to cores
        bind = CpuBinding.BIND_CORES

        if threads_per_core > 1:
            launch_user_options.insert(0, '--hint=multithread')
        elif threads_per_core == 1:
            launch_user_options.insert(0, '--hint=nomultithread')

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  cpus_per_task=cpus_per_task, threads_per_core=threads_per_core,
                  bind=bind, gpus_per_node=gpus_per_node)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)

class AtosAaIntel(Atos):
    """
    Intel compiler-toolchain setup for :any:`AtosAa`
    """

    class AtosAaCpuConfig(CpuConfiguration):
        """Dual-socket AMD EPYC 7H12 (64 core/128 thread, 2.6 GHz)"""

        sockets_per_node = 2
        cores_per_socket = 64
        threads_per_core = 2

    cpu_config = AtosAaCpuConfig

    launcher = SrunLauncher


class AtosAc(Atos):
    """
    Architecture for the Atos ac partition that also offers NVIDIA A100 GPUs.
    """

    class AtosAcCpuConfig(CpuConfiguration):
        """Dual-socket AMD EPYC 7H12 (64 core/128 thread, 2.6 GHz)"""

        sockets_per_node = 2
        cores_per_socket = 64
        threads_per_core = 2
        gpus_per_node = 4

    cpu_config = AtosAcCpuConfig

    launcher = SrunLauncher

class Lumi(Arch):
    # Define the default partition
    partition : str

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, gpus_per_task=None,
            gpus_per_node=None, **kwargs):
        """Build job description using :attr:`cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        # TODO: Ensure proper pinning

        # Fill nodes as much as possible
        max_tasks_per_node = cls.cpu_config.cores_per_node * threads_per_core // cpus_per_task
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, max_tasks_per_node))

        # Use the correct partition.
        launch_user_options = list(as_tuple(launch_user_options))
        launch_user_options.insert(0, f"--partition={cls.partition}")

        # If GPUs are used, limit the number of tasks per node.
        if gpus_per_task:
            if gpus_per_node is not None:
                warning((
                    f'Both, gpus_per_task={gpus_per_task} and gpus_per_node={gpus_per_node} specified, '
                    'ignoring gpus_per_task'
                ))
            else:
                tasks_per_node = min(
                    tasks_per_node,
                    cls.cpu_config.gpus_per_node // gpus_per_task
                )
                gpus_per_node = min(gpus_per_task * tasks_per_node, cls.cpu_config.gpus_per_node)

        if gpus_per_node:
            use_gpu_mpi = kwargs.pop('mpi_gpu_aware', False)

            if use_gpu_mpi:
                env['MPICH_GPU_SUPPORT_ENABLED'] = '1'
                env['MPICH_SMP_SINGLE_COPY_MODE'] = 'NONE'
                env['MPICH_GPU_IPC_ENABLED'] = '0'

        # Bind to cores
        bind = CpuBinding.BIND_CORES

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  cpus_per_task=cpus_per_task, threads_per_core=threads_per_core,
                  bind=bind, gpus_per_node=gpus_per_node)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class LumiC(Lumi):
    """
    Architecture for the LUMI-C partition.
    """

    partition = "standard"

    class LumiCCpuConfig(CpuConfiguration):
        sockets_per_node = 2
        cores_per_socket = 64
        threads_per_core = 2

    cpu_config = LumiCCpuConfig

    launcher = SrunLauncher


class LumiG(Lumi):
    """
    Architecture for the LUMI-G partition. Only 56 cores per node are available
    per node!
    """

    partition = "standard-g"

    class LumiGCpuConfig(CpuConfiguration):
        """
        Single 64 core AMD EPYC 7A53 "Trento" CPU. One core per L3 region is
        deactivated, giving 56 usable cores in total.
        The node is also equipped with four AMD MI250X GPUs which in turn
        contain two GPU dies (the SLURM scheduler treats this as eight distinct
        GPUs).
        The CPU has 128GiB main memory and each MI250X has 2x64GB HBM memory.
        """
        sockets_per_node = 1
        cores_per_socket = 56
        threads_per_core = 2
        gpus_per_node = 8

    cpu_config = LumiGCpuConfig

    launcher = SrunLauncher


arch_registry = {
    None: AtosAaIntel,
    'workstation': Workstation,
    'xc40': XC40Cray,
    'xc40cray': XC40Cray,
    'xc40intel': XC40Intel,
    'atos_aa': AtosAaIntel,
    'atos_ac': AtosAc,
    'lumi_c': LumiC,
    'lumi_g': LumiG
}
"""String-lookup of :any:`Arch` implementations"""
