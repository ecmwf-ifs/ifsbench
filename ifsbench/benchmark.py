from abc import ABC, abstractmethod
from pathlib import Path

from .logging import warning, error
from .util import copy_data, symlink_data


__all__ = ['Benchmark', 'FCBenchmark']


class Benchmark(ABC):
    """
    Definition of a general benchmark setup.
    """

    def __init__(self, **kwargs):
        self.expid = kwargs.get('expid')
        self.rundir = kwargs.get('rundir', None)

        self.ifs = kwargs.get('ifs')

    @property
    @classmethod
    @abstractmethod
    def input_files(self):
        """
        List of relative paths (strings or ``Path`` objects) that
        define all necessary input data files to run this benchmark.
        """
        pass

    @classmethod
    def from_files(cls, **kwargs):
        """
        Create instance of ``Benchmark`` object by globbing a set of
        input paths for the ncessary input data and copying it into rundir.

        :param paths: One or more paths in which the necessary input data can be found
        :param rundir: Run directory to copy/symlink input data into
        :param copy: Copy files intp `rundir` instead of symlinking them
        :param force: Force delete existing input files and re-link/copy
        """
        srcdir = kwargs.get('srcdir')
        rundir = kwargs.get('rundir')
        copy = kwargs.pop('copy', False)
        force = kwargs.pop('force', False)

        # Copy / symlink input files into rundir
        for path in cls.input_files:
            path = Path(path)
            dest = Path(rundir) / path
            srcdir = Path(srcdir)
            candidates = list(srcdir.glob(path.name))
            if len(candidates) == 0:
                warning('Input file %s not found in %s' % (path.name, srcdir))
                continue
            elif len(candidates) == 1:
                source = candidates[0]
            else:
                warning('More than one input file %s found in %s' % (path.name, srcdir))
                source = candidates[0]

            if copy:
                copy_data(source, dest, force=force)
            else:
                symlink_data(source, dest, force=force)

        return cls(**kwargs)

    @classmethod
    def from_tarball(cls):
        """
        Create instance of ``Benchmark`` object from given tarball
        """
        pass

    def to_tarball(self, filepath):
        """
        Dump input files and configuration to a tarball for off-line
        benchmarking.
        """
        pass

    def check_input(self):
        """
        Check input file list matches benchmarjmk configuration.
        """
        for path in self.input_files:
            filepath = self.rundir / path
            if not filepath.exists():
                raise RuntimeError('Required input file %s not found!' % filepath)

    def run(self, **kwargs):
        """
        Run the specified benchmark and validate against stored results.
        """
        if 'rundir' in kwargs:
            if kwargs['rundir'] != self.rundir:
                error('Stored run directory: %s' % self.rundir)
                error('Given run directory:  %s' % kwargs['rundir'])
                raise RuntimeError('Conflicting run directories provided!')
        else:
            kwargs['rundir'] = self.rundir

        self.ifs.run(**kwargs)


class FCBenchmark(Benchmark):
    """
    Definition of a high-res forcecast benchmark.
    """

    pass


class T21FC(FCBenchmark):
    """
    Example configuration of a T21 forceast benchmark.
    """
    pass
