# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Implementation of launch commands for various MPI launchers
"""
from abc import ABC, abstractmethod

from .job import CpuBinding, CpuDistribution
from .logging import debug, warning
from .util import as_tuple


class Launcher(ABC):
    """
    Base class for MPI launch command implementations
    """

    job_options_map: dict
    """
    A mapping of :any:`Job` attributes to launch cmd options

    See :meth:`get_options_from_job` for how this is used to build
    launch command options.
    """

    bind_options_map: dict
    """
    A mapping of :any:`CpuBinding` values to launch cmd options

    See :meth:`get_options_from_binding` for how this is used to build
    launch command options.
    """

    @classmethod
    def get_options_from_job(cls, job):
        """
        Build a list of launch command options from the provided :data:`job` specification

        This uses the :attr:`job_options_map` to compile all options according to what
        is specified in :data:`job`.
        The format of :attr:`job_options_map` should be a `dict` with the name of
        :any:`Job` attributes as keys and launch command-specific format strings as
        values, e.g., ``{'tasks': '--ntasks={}'}``.

        Only attributes from :attr:`job_options_map` that are defined (i.e. do not raise
        :any:`AttributeError`) are added to the list of options, thus this provides a
        direct mapping from the parameters provided to :any:`Job` to the launch command.

        Parameters
        ----------
        job : :any:`Job`
            The job description specifying required hardware resources

        Returns
        -------
        list
            A list of strings with the rendered job options
        """
        options = []
        for attr, option in cls.job_options_map.items():
            try:
                value = getattr(job, attr)
            except AttributeError:
                continue
            options += [option.format(value)]
        return options

    @classmethod
    def get_options_from_binding(cls, bind):
        """
        Build a list of launch command options from the provided :data:`bind` specification

        This uses the :attr:`bind_options_map` to map the specified binding strategy
        to the relevant launch command option. The format of :attr:`bind_options_map`
        should be a `dict` with the binding values declared in the enum :any:`CpuBinding` as
        keys and (a list of) launch-command option strings as values, e.g.,
        ``{CpuBinding.BIND_CORES: '--cpu-bind=cores'}``.

        Parameters
        ----------
        bind : :any:`CpuBinding`

        Returns
        -------
        list
            A list of strings with the rendered job options
        """
        return list(as_tuple(cls.bind_options_map[bind]))

    @classmethod
    @abstractmethod
    def get_launch_cmd(cls, job, user_options=None):
        """
        Return the launch command for a provided :data:`job` specification

        This must be implemented by derived classes.

        Parameters
        ----------
        job : :any:`Job`
            The specification of hardware resources to use
        user_options : list
            Any user-provided options that should be appended to the option
            list of the launch command
        """


class SrunLauncher(Launcher):
    """
    :any:`Launcher` implementation for Slurm's srun
    """

    job_options_map = {
        'nodes': '--nodes={}',
        'tasks': '--ntasks={}',
        'tasks_per_node': '--ntasks-per-node={}',
        'tasks_per_socket': '--ntasks-per-socket={}',
        'cpus_per_task': '--cpus-per-task={}',
        'threads_per_core': '--ntasks-per-core={}',
        'gpus_per_node': '--gres=gpu:{}'
    }

    bind_options_map = {
        CpuBinding.BIND_NONE: ['--cpu-bind=none'],
        CpuBinding.BIND_SOCKETS: ['--cpu-bind=sockets'],
        CpuBinding.BIND_CORES: ['--cpu-bind=cores'],
        CpuBinding.BIND_THREADS: ['--cpu-bind=threads'],
        CpuBinding.BIND_USER: [],
    }

    distribution_options_map = {
        CpuDistribution.DISTRIBUTE_DEFAULT: '*',
        CpuDistribution.DISTRIBUTE_BLOCK: 'block',
        CpuDistribution.DISTRIBUTE_CYCLIC: 'cyclic',
    }

    @classmethod
    def get_distribution_options(cls, job):
        """Return options for task distribution"""
        if not(hasattr(job, 'distribute_remote') or hasattr(job, 'distribute_local')):
            return []

        distribute_remote = getattr(job, 'distribute_remote', CpuDistribution.DISTRIBUTE_DEFAULT)
        distribute_local = getattr(job, 'distribute_local', CpuDistribution.DISTRIBUTE_DEFAULT)

        if distribute_remote is CpuDistribution.DISTRIBUTE_USER:
            debug(('Not applying task distribution options because remote distribution'
                   ' of tasks is set to use user-provided settings'))
            return []
        if distribute_local is CpuDistribution.DISTRIBUTE_USER:
            debug(('Not applying task distribution options because local distribution'
                   ' of tasks is set to use user-provided settings'))
            return []

        return [(f'--distribution={cls.distribution_options_map[distribute_remote]}'
                 f':{cls.distribution_options_map[distribute_local]}')]


    @classmethod
    def get_launch_cmd(cls, job, user_options=None):
        """
        Return the srun command for the provided :data:`job` specification
        """

        cmd = ['srun'] + cls.get_options_from_job(job)
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_distribution_options(job)
        if user_options is not None:
            cmd += list(as_tuple(user_options))
        return cmd


class AprunLauncher(Launcher):
    """
    :any:`Launcher` implementation for Cray's aprun
    """

    job_options_map = {
        'tasks': '-n {}',
        'tasks_per_node': '-N {}',
        'tasks_per_socket': '-S {}',
        'cpus_per_task': '-d {}',
        'threads_per_core': '-j {}',
    }

    bind_options_map = {
        CpuBinding.BIND_NONE: ['-cc none'],
        CpuBinding.BIND_SOCKETS: ['-cc numa_node'],
        CpuBinding.BIND_CORES: ['-cc cpu'],
        CpuBinding.BIND_THREADS: ['-cc depth'],
        CpuBinding.BIND_USER: [],
    }

    @classmethod
    def get_distribution_options(cls, job):
        """Return options for task distribution"""
        do_nothing = [CpuDistribution.DISTRIBUTE_DEFAULT, CpuDistribution.DISTRIBUTE_USER]
        if hasattr(job, 'distribute_remote') and job.distribute_remote not in do_nothing:
            warning('Specified remote distribution option ignored in AprunLauncher')
        if hasattr(job, 'distribute_local') and job.distribute_local not in do_nothing:
            warning('Specified local distribution option ignored in AprunLauncher')

        return []

    @classmethod
    def get_launch_cmd(cls, job, user_options=None):
        """
        Return the aprun command for the provided :data:`job` specification
        """

        cmd = ['aprun']
        # Aprun has no option to specify node counts and tasks relative to
        # nodes, thus we derive the number of total tasks if
        # it has not been specified explicitly
        if not hasattr(job, 'tasks'):
            cmd += [f'-n {job.get_tasks()}']
        cmd += cls.get_options_from_job(job)
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_distribution_options(job)
        if user_options is not None:
            cmd += list(as_tuple(user_options))
        return cmd


class MpirunLauncher(Launcher):
    """
    :any:`Launcher` implementation for a standard mpirun
    """

    job_options_map = {
        'tasks': '-np {}',
        'tasks_per_node': '-npernode {}',
        'tasks_per_socket': '-npersocket {}',
        'cpus_per_task': '-cpus-per-proc {}',
    }

    bind_options_map = {
        CpuBinding.BIND_NONE: ['--bind-to none'],
        CpuBinding.BIND_SOCKETS: ['--bind-to socket'],
        CpuBinding.BIND_CORES: ['--bind-to core'],
        CpuBinding.BIND_THREADS: ['--bind-to hwthread'],
        CpuBinding.BIND_USER: [],
    }

    distribution_options_map = {
        CpuDistribution.DISTRIBUTE_BLOCK: 'core',
        CpuDistribution.DISTRIBUTE_CYCLIC: 'numa',
    }

    @classmethod
    def get_distribution_options(cls, job):
        """Return options for task distribution"""
        do_nothing = [CpuDistribution.DISTRIBUTE_DEFAULT, CpuDistribution.DISTRIBUTE_USER]
        if hasattr(job, 'distribute_remote') and job.distribute_remote not in do_nothing:
            warning('Specified remote distribution option ignored in MpirunLauncher')

        if not hasattr(job, 'distribute_local') or job.distribute_local in do_nothing:
            return []

        return [f'--map-by {cls.distribution_options_map[job.distribute_local]}']

    @classmethod
    def get_launch_cmd(cls, job, user_options=None):
        """
        Return the mpirun command for the provided :data:`job` specification
        """

        cmd = ['mpirun']
        # Mpirun has no option to specify tasks relative to nodes without also
        # modifying the mapping, thus we derive the number of total tasks if
        # it has not been specified explicitly
        if not hasattr(job, 'tasks'):
            cmd += [f'-np {job.get_tasks()}']
        cmd += cls.get_options_from_job(job)
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_distribution_options(job)
        if user_options is not None:
            cmd += list(as_tuple(user_options))
        return cmd
