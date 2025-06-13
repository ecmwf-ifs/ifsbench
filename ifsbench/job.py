# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Hardware and job resource description classes
"""
from abc import ABC
from enum import Enum, auto
from .logging import error
from .util import classproperty


__all__ = ['CpuConfiguration', 'CpuBinding', 'CpuDistribution', 'Job']


class CpuConfiguration(ABC):
    """
    Abstract base class to describe the hardware configuration of compute nodes

    :any:`Arch` should provide an implementation of this class to describe the
    CPU configuration of the available nodes.

    Attributes
    ----------
    sockets_per_node : int
        The number of sockets (sometimes this is also used to describe NUMA domains)
        available on each node. This must be specified in a derived class.
    cores_per_socket : int
        The number of physical cores per socket. This must be specified in a derived class.
    threads_per_core : int
        The number of logical cores per physical core (i.e. the number of SMT threads
        each core can execute). Typically, this is 1 (no hyperthreading), 2 or 4.
        This must be specified in a derived class.
    cores_per_node : int
        The number of physical cores per node. This value is automatically derived
        from the above properties.
    threads_per_node : int
        The number of logical cores per node (threads). This value is automatically derived
        from the above properties.
    gpus_per_node : int
        The number of available GPUs per node.
    """

    sockets_per_node: int

    cores_per_socket: int

    threads_per_core: int

    gpus_per_node = 0

    @classproperty
    def cores_per_node(self):
        """
        The number of physical cores per node
        """
        return self.sockets_per_node * self.cores_per_socket

    @classproperty
    def threads_per_node(self):
        """
        The number of logical cores (threads) per node
        """
        return self.cores_per_node * self.threads_per_core


class CpuBinding(Enum):
    """
    Description of CPU binding strategy to use, for which the launch
    command should provide the appropriate options
    """
    BIND_NONE = auto()
    """Disable all binding specification"""

    BIND_SOCKETS = auto()
    """Bind tasks to sockets"""

    BIND_CORES = auto()
    """Bind tasks to cores"""

    BIND_THREADS = auto()
    """Bind tasks to hardware threads"""

    BIND_USER = auto()
    """Indicate that a different user-specified strategy should be used"""


class CpuDistribution(Enum):
    """
    Description of CPU distribution strategy to use, for which the launch
    command should provide the appropriate options
    """
    DISTRIBUTE_DEFAULT = auto()
    """Use the default distribution strategy"""

    DISTRIBUTE_BLOCK = auto()
    """Allocate ranks/threads consecutively"""

    DISTRIBUTE_CYCLIC = auto()
    """Allocate ranks/threads in a round-robin fashion"""

    DISTRIBUTE_USER = auto()
    """Indicate that a different user-specified strategy should be used"""

class Job:
    """
    Description of a parallel job's resource requirements

    Provided with a CPU configuration (:data:`cpu_config`) and at least one of

    * the total number of MPI tasks (:data:`tasks`)
    * the number of nodes (:data:`nodes`) and the number of tasks per node
      (:data:`tasks_per_node`)
    * the number of nodes (:data:`nodes`) and the number of tasks per socket
      (:data:`tasks_per_socket`)

    this class specifies the resource requirements for a job.

    The underlying idea is to specify as little as possible which is then passed on
    to the relevant launch command but with the possibility to estimate those values
    that can be derived unambigously from the specified values.

    The relevant attributes (with the same names as the parameters to the constructor)
    are only defined when the corresponding value has been specified explicitly (with
    the exception of those that have a default value), i.e., accessing undefined
    attributes will raise a :any:`AttributeError`. The corresponding ``get_`` methods
    allow to derive the relevant values when it is unambigously possible, or raise an
    :any:`AttributeError` otherwise.

    Multi-threading can be specified by providing a value larger than 1 (the default)
    for :data:`cpus_per_task`. Symmetric multi-threading (hyperthreading) can be
    enabled with a value greater than 1 in :data:`threads_per_core`.

    The desired pinning strategy can be specified with :data:`bind`.

    Parameters
    ----------
    cpu_config : :any:`CpuConfiguration`
        The description of the available CPUs in the target system.
    tasks : int, optional
        The total number of MPI tasks to be used.
    nodes : int, optional
        The total number of nodes to be used.
    tasks_per_node : int, optional
        Launch a specific number of tasks per node. Can be derived from :attr:`tasks_per_socket`
        if that is specified
    tasks_per_socket : int, optional
        Launch a specific number of tasks per socket
    cpus_per_task : int, optional
        The number of computing elements (threads) available to each task for hybrid jobs.
    threads_per_core : int, optional
        Enable symmetric multi-threading (hyperthreading).
    bind : :any:`CpuBinding`, optional
        Specify the binding strategy to use for pinning.
    distribute_remote : :any:`CpuDistribution`, optional
        Specify the distribution strategy to use for task distribution across nodes
    distribute_local : :any:`CpuDistribution`, optional
        Specify the distribution strategy to use for task distribution across sockets within a node
    gpus_per_node : int, optional
        The number of GPUs that are used per node.
    """

    def __init__(self, cpu_config, tasks=None, nodes=None, tasks_per_node=None,
                 tasks_per_socket=None, cpus_per_task=None, threads_per_core=None,
                 bind=None, distribute_remote=None, distribute_local=None,
                 gpus_per_node=None):

        assert issubclass(cpu_config, CpuConfiguration)
        self.cpu_config = cpu_config
        if tasks is not None:
            self.tasks = tasks
        if nodes is not None:
            self.nodes = nodes
        if tasks_per_node is not None:
            self.tasks_per_node = tasks_per_node
        if tasks_per_socket is not None:
            self.tasks_per_socket = tasks_per_socket
        if cpus_per_task is not None:
            self.cpus_per_task = cpus_per_task
        if threads_per_core is not None:
            self.threads_per_core = threads_per_core
        if gpus_per_node is not None:
            self.gpus_per_node = gpus_per_node
        if bind is not None:
            self.bind = bind
        if distribute_remote is not None:
            self.distribute_remote = distribute_remote
        if distribute_local is not None:
            self.distribute_local = distribute_local


        if self.get_gpus_per_node() > self.cpu_config.gpus_per_node:
            raise ValueError("More GPUs have been requested than are available.")

        try:
            tasks = self.get_tasks()
            nodes = self.get_nodes()
            threads = self.get_threads()
        except AttributeError as excinfo:
            error(('Need to specify at least one of:\n'
                   'number of tasks or (tasks_per_node and nodes) or (tasks_per_socket and nodes)'))
            raise excinfo

        if nodes < 1:
            error(f'Invalid number of nodes: {nodes}')
            raise ValueError
        if tasks < 1:
            error(f'Invalid number of tasks: {nodes}')
            raise ValueError
        if threads < tasks:
            error(f'Invalid number of threads: {threads}')
            raise ValueError

    def get_tasks(self):
        """
        The total number of MPI tasks

        If this has not been specified explicitly, it is estimated as
        ``nodes * tasks_per_node``.
        """
        tasks = getattr(self, 'tasks', None)
        if tasks is None:
            return self.get_nodes() * self.get_tasks_per_node()
        return tasks

    def get_nodes(self):
        """
        The total number of nodes

        If this has not been specified explicitly, it is estimated as
        ``ceil(threads / available_threads_per_node)`` with the number of
        available threads dependent on the use of SMT.
        """
        nodes = getattr(self, 'nodes', None)
        if nodes is None:
            threads_per_node = self.get_tasks_per_node() * self.get_threads_per_core() * self.get_cpus_per_task()


            return (self.get_threads() + threads_per_node - 1) // threads_per_node

        return nodes

    def get_tasks_per_node(self):
        """
        The number of tasks on each node

        If this has not been specified explicitly, it is estimated as
        ``tasks_per_socket * sockets_per_node``.
        """

        if hasattr(self, 'tasks_per_node'):
            # If tasks_per_node was specified just return it.
            tasks_per_node = self.tasks_per_node
        else:
            # If tasks_per_node wasn't specified, calculate it from the other
            # values.

            if hasattr(self, 'tasks_per_socket'):
                tasks_per_node = self.tasks_per_socket * self.cpu_config.sockets_per_node
            elif hasattr(self, 'tasks'):
                tasks_per_node = self.cpu_config.cores_per_node // self.get_cpus_per_task()
            else:
                raise ValueError('The number of tasks per node could not be determined!')

        return tasks_per_node

    def get_cpus_per_task(self):
        """
        The number of CPUs assigned to each task

        If this has not been specified explicitly, it defaults to 1
        """
        return getattr(self, 'cpus_per_task', 1)

    def get_gpus_per_node(self):
        """
        The number of GPUs to use per node

        If this has not been specified explicitly, it defaults to 0
        """
        return getattr(self, 'gpus_per_node', 0)

    def get_threads_per_core(self):
        """
        The number of threads assigned to each core (symmetric multi threading
        or hyperthreading for values greater than 1)

        If this has not been specified explicitly, it defaults to 1
        """
        return getattr(self, 'threads_per_core', 1)

    def get_threads(self):
        """
        The total number of threads across all tasks

        This is derived automatically as ``tasks * cpus_per_task``
        """
        return self.get_tasks() * self.get_cpus_per_task()
