# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from pathlib import Path
from os import getenv

from ifsbench.drhook import DrHook
from ifsbench.logging import warning
from ifsbench.namelist import IFSNamelist

# Note: all IFS subclasses registered in cycle_registry are also exported
# at the end of this file
__all__ = ['IFS', 'cycle_registry']


class IFS(ABC):
    """
    Manage environment setup, configuration sanity checks and execution of IFS

    This class is specialized for every supported release of the IFS (called
    cycle). It is instantiated via the factory method :meth:`IFS.create_cycle`,
    using the subclass corresponding to the provided cycle.
    See :any:`cycles_registry` for all available cycles.

    Parameters
    ----------
    builddir : str or :any:`pathlib.Path`
        The build directory of the IFS.
    sourcedir : str or :any:`pathlib.Path`, optional
        The source code directory of the IFS.
    installdir : str or :any:`pathlib.Path`, optional
        The install directory of the IFS.
    nml_template : str or :any:`pathlib.Path`, optional
        The path to a namelist template.
    """

    def __init__(self, builddir, sourcedir=None, installdir=None, nml_template=None):
        assert getattr(self, 'cycle').startswith('cy')
        self.builddir = Path(builddir)
        self.sourcedir = None if sourcedir is None else Path(sourcedir)
        self.installdir = None if installdir is None else Path(installdir)
        self.nml_template = nml_template

    @staticmethod
    def create_cycle(cycle, *args, **kwargs):
        """
        Parameters
        ----------
        cycle : str
            The name of the IFS cycle to instantiate.
        *args :
            Positional arguments to provide to the cycle constructor
        **kwargs :
            Keyword arguments to provide to the cycle constructor
        """
        if cycle is None or cycle.lower() not in cycle_registry:
            warning(f'Cycle "{cycle}" not found, using the default ({cycle_registry["default"].cycle})')
            cycle = 'default'
        return cycle_registry[cycle.lower()](*args, **kwargs)

    @property
    @abstractmethod
    def exec_name(self):
        """
        The name of the binary to run
        """

    @property
    def executable(self):
        """
        Primary executable to run

        This prefers the binary from the install directory, if given, otherwise
        uses the binary from the build directory.

        Returns
        -------
        pathlib.Path
            The path to the executable
        """
        if self.installdir is not None:
            return (self.installdir/'bin')/self.exec_name
        return (self.builddir/'bin')/self.exec_name

    @property
    def ld_library_paths(self):
        """
        List of paths that need to be available in ``LD_LIBRARY_PATH``
        """
        return ()

    def verify_namelist(self, namelist):
        """
        Check correctness of namelist entries against compiled
        namelist headers.
        """
        raise NotImplementedError('Not yet done...')

    def setup_env(self, namelist, rundir, nproc, nproc_io, nthread, hyperthread, arch, **kwargs):
        # pylint: disable=unused-argument
        """
        Define run environment

        This is called by :meth:`IFS.run` and should be overriden by cycle-specific
        classes where necessary to add/modify the default environment defined here.

        See :meth:`IFS.run` for a description of parameters and below for
        additional arguments used from :attr:`kwargs`.

        Parameters
        ----------
        env : dict, optional
            An existing environment definition to use and complement
        drhook : :any:`DrHook`, optional
            Environment definitions for DrHook profiling

        Returns
        -------
        (env, kwargs) : (dict, dict)
            The run environment and the updated kwargs dict with env-specific
            entries removed.
        """
        # Initialize environment
        env = kwargs.pop('env', None)
        env = {} if env is None else env

        # Define the run directory as data directory to the IFS
        assert rundir
        env['DATA'] = str(rundir)

        # Set up DrHook according to preset
        drhook = kwargs.pop('drhook', None)
        if drhook is not None:
            assert isinstance(drhook, DrHook)
            env.update(drhook.env)

        # Add GRIB-specific paths
        env['GRIB_DEFINITION_PATH'] = str(self.builddir/'share/eccodes/definitions')
        env['GRIB_SAMPLES_PATH'] = str(self.builddir/'share/eccodes/ifs_samples/grib1_mlgrib2')

        # Set number of MPI processes and OpenMP threads
        assert isinstance(nproc, int) and isinstance(nproc_io, int)
        env['NPROC'] = nproc - nproc_io
        env['NPROC_IO'] = nproc_io

        # Make LD_LIBRARY_PATH entries available
        if self.ld_library_paths:
            env.setdefault('LD_LIBRARY_PATH', getenv('LD_LIBRARY_PATH', ''))
            env['LD_LIBRARY_PATH'] = ':'.join([*self.ld_library_paths, env['LD_LIBRARY_PATH']])

        return env, kwargs

    def setup_nml(self, namelist, rundir, nproc, nproc_io, nthread, hyperthread, arch, **kwargs):
        # pylint: disable=unused-argument
        """
        Setup the IFS namelist

        This should be overridden by cycle-specific classes where necessary to
        add/modify the namelist created here.

        See :meth:`IFS.run` for a description of parameters and below for
        additional arguments used from :attr:`kwargs`.

        Parameters
        ----------
        fclen : str, optional
            Override the length of the forecast run (e.g., ``'h240'`` or
            ``'d10'``).

        Returns
        -------
        (nml, kwargs) : (:any:`IFSNamelist`, dict)
            The config file and the updated kwargs dict with namelist-specific
            entries removed.
        """
        nml = IFSNamelist(namelist=namelist, template=self.nml_template)

        # Insert the number of MPI ranks into the config file
        assert isinstance(nproc, int) and isinstance(nproc_io, int)
        nml['NAMPAR0']['NPROC'] = nproc - nproc_io
        if 'NAMIO_SERV' in nml:
            nml['NAMIO_SERV']['NPROC_IO'] = nproc_io

        # Modify forecast length
        fclen = kwargs.pop('fclen', None)
        if fclen is not None:
            nml['NAMRIP']['CSTOP'] = fclen

        return nml, kwargs

    def run(self, namelist, rundir, nproc=1, nproc_io=0, nthread=1, hyperthread=1, arch=None, **kwargs):
        """
        Set-up environment and configuration file and launch an IFS execution

        This calls :meth:`IFS.setup_env` and :meth:`IFS.setup_nml` before
        invoking the architecture's :any:`Arch.run` method.

        Parameters
        ----------
        namelist : :any:`f90nml.Namelist` or NoneType
            A namelist to use as a basis for the IFS run that will be further
            modified by :meth:`IFS.setup_nml`
        rundir : str or :any:`pathlib.Path`
            The run directory for IFS execution
        nproc : int, optional
            The total number of MPI ranks
        nproc_io : int, optional
            The number of MPI ranks for the IO server
        nthread : int, optional
            The number of OpenMP threads to use per MPI rank
        hyperthread : int, optional
            The number of hyperthreads to use per physical core
        arch : str or :any:`Arch`, optional
            The architecture definition to use
        **kwargs :
            Further named parameters that will be passed to
            :meth:`IFS.setup_env`, :meth:`IFS.setup_nml` and :meth:`Arch.run`
        """

        # Setup the run environment
        env, kwargs = self.setup_env(namelist=namelist, rundir=rundir, nproc=nproc, nproc_io=nproc_io,
                                     nthread=nthread, hyperthread=hyperthread, arch=arch, **kwargs)

        # Setup the IFS namelist
        nml, kwargs = self.setup_nml(namelist=namelist, rundir=rundir, nproc=nproc, nproc_io=nproc_io,
                                     nthread=nthread, hyperthread=hyperthread, arch=arch, **kwargs)

        # Write the input namelist
        nml.write(rundir/'fort.4', force=True)

        # Run it
        cmd = [str(self.executable)]
        arch.run(cmd=cmd, tasks=nproc, cpus_per_task=nthread, threads_per_core=hyperthread,
                 env=env, cwd=rundir, **kwargs)


class IFS_CY46R1(IFS):

    cycle = 'cy46r1'

    @property
    def exec_name(self):
        return 'ifsMASTER.DP'

    @property
    def ld_library_paths(self):
        """
        List of paths that need to be available in ``LD_LIBRARY_PATH``

        Inserts ``builddir/ifs-source`` into ``LD_LIBRARY_PATH`` so
          ``libblack.so`` is picked up.
        """
        return (str(self.builddir/'ifs-source'),)


class IFS_CY47R1(IFS):

    cycle = 'cy47r1'

    def __init__(self, *args, prec='dp', **kwargs):
        super().__init__(*args, **kwargs)

        prec = prec.lower()
        if prec in ('double', 'dp'):
            self.prec = 'dp'
        elif prec in ('single', 'sp'):
            self.prec = 'sp'
        else:
            raise ValueError(f'Invalid precision: {prec}')

    @property
    def exec_name(self):
        return f'ifsMASTER.{self.prec.upper()}'

    @property
    def ld_library_paths(self):
        """
        List of paths that need to be available in ``LD_LIBRARY_PATH``

        Inserts ``builddir/ifs_dp`` into ``LD_LIBRARY_PATH`` so
          ``libblack.so`` is picked up.
        """
        return (str(self.builddir/f'ifs_{self.prec.lower()}'),)


class IFS_CY47R2(IFS_CY47R1):
    cycle = 'cy47r2'


class IFS_CY48(IFS_CY47R1):
    cycle = 'cy48'


cycle_registry = {
    'default': IFS_CY47R2,

    'cy46r1': IFS_CY46R1,
    'cy47r1': IFS_CY47R1,
    'cy47r2': IFS_CY47R2,
    'cy48': IFS_CY48,
}
"""Registry of available IFS cycles and the corresponding classes"""


# Export all cycle_registry classes
__all__ += [cls.__name__ for cls in set(cycle_registry.values())]
