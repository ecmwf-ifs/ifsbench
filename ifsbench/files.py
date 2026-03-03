# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Data structures to represent IFS input files
"""

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import glob
import yaml

from ifsbench.logging import header, success, warning
from ifsbench.util import execute, as_tuple


__all__ = ['InputFile', 'ExperimentFiles']


class InputFile:
    """
    Representation of a single input file together with some meta data

    Parameters
    ----------
    path : str or :any:`pathlib.Path`
        The path of the input file
    src_dir : str or :any:`pathlib.Path`, optional
        The base directory relative to which :attr:`path` is interpreted.
    compute_metadata : bool, optional
        Compute meta data for that file (such as SHA-256 checksum and size).
    """

    def __init__(self, path, src_dir=None, compute_metadata=True):
        if src_dir is None:
            src_dir = '/'
        self._src_dir = Path(src_dir)
        self._path = Path(path).relative_to(self.src_dir)
        self._original_path = Path(path)

        if compute_metadata:
            self.checksum = self._sha256sum(self.fullpath)
            self.size = self._size(self.fullpath)
        else:
            self.checksum = None
            self.size = None

    @classmethod
    def from_dict(cls, data, src_dir=None, verify_checksum=True):
        """
        Create :any:`InputFile` from a dict representation

        Parameters
        ----------
        data : dict
            The dict representation, e.g. created by :meth:`to_dict`
        src_dir : str or :any:`pathlib.Path`, optional
            The base directory relative to which the path should be stored.
        verify_checksum : bool, optional
            Verify that checksum in dict matches the file.
        """
        path, meta = data.popitem()
        assert not data
        obj = cls(meta['fullpath'], src_dir=src_dir, compute_metadata=verify_checksum)
        if verify_checksum:
            if meta['sha256sum'] != obj.checksum:
                raise ValueError(f'Checksum for {path} does not match')
        else:
            obj.checksum = meta.get('sha256sum')
            obj.size = meta.get('size')
        return obj

    def to_dict(self):
        """Create a `dict` representation of the meta data for this file"""
        data = {'fullpath': str(self.fullpath)}
        if self.checksum:
            data['sha256sum'] = self.checksum
        if self.size:
            data['size'] = self.size
        return {str(self.path): data}

    @property
    def fullpath(self):
        """The full path of the file"""
        return self.src_dir / self._path

    @property
    def original_path(self):
        """The original path of the file used during construction of the object"""
        return self._original_path

    @property
    def path(self):
        """The path of the file relative to :attr:`src_dir`"""
        return self._path

    @property
    def src_dir(self):
        """The base directory under which the file is located"""
        return self._src_dir

    @src_dir.setter
    def src_dir(self, src_dir):
        """Update the base directory relative to which the file is located"""
        path = Path(self.fullpath).relative_to(src_dir)
        self._src_dir = Path(src_dir)
        self._path = path

    @staticmethod
    def _sha256sum(filepath):
        """Create SHA-256 checksum for the file at the given path"""

        filepath = Path(filepath)

        # Use 4MB chunks for reading the file (reading it completely into
        # memory will be a bad idea for large GRIB files).
        chunk_size = 4 * 1024 * 1024
        sha = sha256()

        with filepath.open('rb') as f:
            chunk = f.read(chunk_size)
            while chunk:
                sha.update(chunk)
                chunk = f.read(chunk_size)

        return sha.hexdigest()

    @staticmethod
    def _size(filepath):
        """Obtain file size in byte for the file at the given path"""
        filepath = Path(filepath)
        return filepath.stat().st_size

    def __hash__(self):
        """
        Custom hash function using :attr:`InputFile.checksum`, if
        available, and :attr:`InputFile.fullpath` otherwise.
        """
        return hash(self.checksum or self.fullpath)

    def __eq__(self, other):
        """
        Compare to another object

        If available, compare :attr:`InputFile.checksum`, otherwise
        rely on :attr:`InputFile.fullpath`.
        """
        if not isinstance(other, InputFile):
            return False
        if not self.checksum or not other.checksum:
            return self.fullpath == other.fullpath
        return self.checksum == other.checksum


class ExperimentFiles:
    """
    Helper class to store the list of files required to run an experiment

    It provides capabilities to pack and unpack tarballs of these files
    to prepare an experiment for external runs.

    Parameters
    ----------
    exp_id : str
        The id of the experiment
    src_dir : (list of) str or :any:`pathlib.Path`, optional
        One or more source directories from which input data to take.
        If given, files are searched for in these paths.
    """

    def __init__(self, exp_id, src_dir=None):
        self.exp_id = exp_id
        self.src_dir = tuple(Path(s) for s in as_tuple(src_dir))
        self._files = set()

    @classmethod
    def from_yaml(cls, input_path, verify_checksum=True):
        """
        Load :any:`ExperimentFiles` from a YAML file

        Parameters
        ----------
        input_path : str or :any:`pathlib.Path`
            The file name of the YAML file.
        verify_checksum : bool, optional
            Verify checksum of all files.
        """
        with Path(input_path).open(encoding='utf-8') as f:
            return cls.from_dict(yaml.safe_load(f), verify_checksum=verify_checksum)

    @classmethod
    def from_dict(cls, data, verify_checksum=True):
        """
        Create :any:`ExperimentFiles` from `dict` representation

        Parameters
        ----------
        data : dict
            The dictionary representation, e.g. as created by :meth:`to_dict`.
        verify_checksum : bool, optional
            Verify checksum of all files.
        """
        exp_id, src_dir_files = data.popitem()
        assert not data
        src_dir = list(src_dir_files.keys())
        obj = cls(exp_id, src_dir=src_dir)
        obj._files = {  # pylint: disable=protected-access
            InputFile.from_dict({p: f}, src_dir=src_dir, verify_checksum=verify_checksum)
            for src_dir, files in src_dir_files.items()
            for p, f in files.items()
        }
        return obj

    def to_yaml(self, output_path):
        """
        Save list of experiment files and their meta data as a YAML file.

        Parameters
        ----------
        output_path : str or :any:`pathlib.Path`
            File name for the YAML file.
        """
        with Path(output_path).open('w', encoding='utf-8') as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)

    def to_dict(self):
        """
        Create a dictionary containing the list of experiment files and the
        meta data stored for them.
        """
        data = defaultdict(dict)
        for f in self.files:
            data[str(f.src_dir)].update(f.to_dict())
        return {self.exp_id: dict(data)}

    def _input_file_in_src_dir(self, input_file, verify_checksum=False):
        """
        Find :attr:`input_file` in :attr:`ExperimentFiles.src_dir`

        The file is identified by comparing file name and checksum.
        """
        # Nothing to do if we don't have a base relative to which to look
        if not self.src_dir:
            return input_file

        # Let's see if the input_file is relative to one of the src directories
        for src_dir in self.src_dir:
            try:
                path = Path(input_file.fullpath).relative_to(src_dir)
            except ValueError:
                continue
            input_file.src_dir = src_dir
            return input_file

        # input_file is not relative to one of the src directories. Let's see if
        # we can find something that matches
        candidates = [
            (path, src_dir)
            for src_dir in self.src_dir
            for path in glob.iglob(str(src_dir / '**' / input_file.path.name), recursive=True)
        ]

        # Sort the candidates by the overlap (judged from the end) in an attempt to
        # minimize the number of files to try
        def _score_overlap_from_behind(string):
            try:
                return [i == j for i, j in zip(reversed(str(input_file)), reversed(string))].index(
                    False
                )
            except ValueError:
                return min(len(input_file), len(string))

        candidates.sort(key=_score_overlap_from_behind, reverse=True)

        for path, src_dir in candidates:
            try:
                candidate_file = InputFile(path, src_dir)
            except OSError:
                continue
            if candidate_file.checksum == input_file.checksum:
                return candidate_file

        if verify_checksum:
            raise ValueError(
                f'Input file {input_file.path} not found relative to source directories'
            )
        warning('Input file %s not found relative to source directories', input_file.path)
        return input_file

    def add_file(self, *filepath, compute_metadata=True):
        """
        Add one or more files to the list of input files for the experiment

        Parameters
        ----------
        filepath : (list of) str or :any:`pathlib.Path`
            One or multiple file paths to add.
        """
        filepath = [InputFile(path, compute_metadata=compute_metadata) for path in filepath]
        self.add_input_file(*filepath, verify_checksum=compute_metadata)

    def add_input_file(self, *input_file, verify_checksum=True):
        """
        Add one or more :any:`InputFile` to the list of input files

        Parameters
        ----------
        Input_file : (list of) :any:`InputFile`
            One or multiple input file instances to add.
        """
        for f in input_file:
            try:
                new_file = self._input_file_in_src_dir(f, verify_checksum=verify_checksum)
                self._files.add(new_file)
            except ValueError:
                warning('Skipping input file %s', f.path)

    def update_srcdir(self, src_dir, update_files=True, with_ifsdata=False):
        """
        Change the :attr:`ExperimentFiles.src_dir` relative to which input
        files are searched

        Parameters
        ----------
        src_dir : (list of) str or :any:`pathlib.Path`, optional
            One or more source directories.
        update_files : bool, optional
            Update paths for stored files. This verifies checksums.
        with_ifsdata : bool, optional
            Include ifsdata files in the update.
        """
        self.src_dir = as_tuple(src_dir)

        if update_files:
            if with_ifsdata:
                old_files = self.files
                new_files = set()
            else:
                old_files = self.exp_files
                new_files = self.ifsdata_files
            while old_files:
                new_file = self._input_file_in_src_dir(old_files.pop(), verify_checksum=True)
                new_files.add(new_file)
            self._files = new_files

    @property
    def files(self):
        """
        The set of :any:`InputFile` for the experiment
        """
        return self._files.copy()

    @property
    def exp_files(self):
        """
        The set of experiment-specific :any:`InputFile`
        """
        return {f for f in self._files if '/ifsdata/' not in str(f.fullpath)}

    @property
    def ifsdata_files(self):
        """
        The set of static ifsdata files used by the experiment
        """
        return {f for f in self._files if '/ifsdata/' in str(f.fullpath)}

    @staticmethod
    def _create_tarball(files, output_basename, basedir=None):
        """
        Create a tarball containing :attr:`files`

        Parameters
        ----------
        files : list of str
            The files to be included in the tarball.
        output_basename : str
            The base name without suffix of the tarball.
        basedir : str, optional
            If given, :attr:`files` are interpreted as relative to this.
        """
        output_file = Path(output_basename).with_suffix('.tar.gz')
        header('Creating tarball %s...', str(output_file))
        cmd = ['tar', 'cvzhf', str(output_file)]
        if basedir:
            cmd += ['-C', str(basedir)]
        cmd += files
        execute(cmd)
        success('Finished creating tarball')

    def to_tarball(self, output_dir, with_ifsdata=False):
        """
        Create tarballs containing all input files

        Parameters
        ----------
        output_dir : str or :any:`pathlib.Path`
            Output directory for tarballs.
        with_ifsdata : bool, optional
            Create also a tarball containing the ifsdata files used by
            this experiment (default: disabled).
        """
        output_dir = Path(output_dir)

        exp_files = defaultdict(list)
        for f in self.exp_files:
            exp_files[f.src_dir] += [str(f.path)]
        for src_dir, files in exp_files.items():
            output_basename = output_dir / (src_dir.name or 'other')
            self._create_tarball(files, output_basename, basedir=src_dir)

        if with_ifsdata:
            ifsdata_files = list(self.ifsdata_files)
            if ifsdata_files:
                basedir = ifsdata_files[0].src_dir
                files = [str(f.path) for f in ifsdata_files]
                output_basename = output_dir / 'ifsdata'
                self._create_tarball(files, output_basename, basedir=basedir)

    @staticmethod
    def _extract_tarball(filepath, output_dir):
        """
        Extract a tarball

        Parameters
        ----------
        filepath : str or :any:`pathlib.Path`
            The file path for the tarball
        output_dir : str or :any:`pathlib.Path`
            Output directory for extracted files.
        """
        filepath = Path(filepath).resolve()
        header('Extracting tarball %s', str(filepath))
        cmd = ['tar', 'xvzf', str(filepath)]
        execute(cmd, cwd=str(output_dir))
        success('Finished extracting tarball')

    @classmethod
    def from_tarball(
        cls,
        summary_file,
        input_dir,
        output_dir,
        ifsdata_dir=None,
        with_ifsdata=False,
        verify_checksum=True,
    ):
        """
        Create :any:`ExperimentFiles` from a summary file and unpack corresponding tarballs
        containing the files

        Parameters
        ----------
        summary_file : str or :any:`pathlib.Path`
            The file path for the YAML file
        input_dir : (list of) str or :any:`pathlib.Path`
            One or multiple input directories to search recursively for tarballs.
        output_dir : str or :any:`pathlib.Path`
            Output directory for files after unpacking tarballs.
        ifsdata_dir : str or :any:`pathlib.Path`, optional
            Directory to look for ifsdata files (default: :data:`output_dir`).
        with_ifsdata : bool, optional
            Look for an `ifsdata.tar.gz` tarball in the same directories as the
            experiment file tarballs and unpack it to :data:`ifsdata_dir` (default: disabled).
        verify_checksum : bool, optional
            Verify that all files exist and checksums match (default: enabled).
        """
        summary_file = Path(summary_file).resolve()
        obj = cls.from_yaml(summary_file, verify_checksum=False)

        # Find all tarballs for experiment files
        input_dir = [Path(path).resolve() for path in as_tuple(input_dir)]
        tarballs = set()
        for f in obj.exp_files:
            tarball_name = f'{f.src_dir.name}.tar.gz'
            candidates = [
                path
                for src_dir in input_dir
                for path in glob.iglob(str(src_dir / '**' / tarball_name), recursive=True)
            ]
            if not candidates:
                raise ValueError(f'Archive {tarball_name} not found in input directories')
            if len(candidates) > 1:
                warning(
                    'Found multiple candidates for %s, using the first: %s',
                    tarball_name,
                    ', '.join(candidates),
                )
            tarballs.add(candidates[0])

        # Add ifsdata tarball
        ifsdata_tarball = None
        if with_ifsdata:
            if tarballs:
                candidates = list({Path(path).with_name('ifsdata.tar.gz') for path in tarballs})
            else:
                candidates = [Path(path) / 'ifsdata.tar.gz' for path in input_dir]
            candidates = [str(path) for path in candidates if path.exists()]
            if not candidates:
                raise ValueError('ifsdata.tar.gz not found in any experiment tarball directory')
            if len(candidates) > 1:
                warning(
                    'Found multiple candidates for ifsdata.tar.gz, using the first: %s',
                    ', '.join(candidates),
                )
            ifsdata_tarball = candidates[0]

        # Extract all tarballs
        output_dir = (Path(output_dir) / obj.exp_id).resolve()
        if tarballs:
            output_dir.mkdir(exist_ok=True)
            for tarball in tarballs:
                cls._extract_tarball(tarball, output_dir)

        if ifsdata_dir is None:
            ifsdata_dir = output_dir
        else:
            ifsdata_dir = Path(ifsdata_dir).resolve()
        if ifsdata_tarball is not None:
            ifsdata_dir.mkdir(exist_ok=True)
            cls._extract_tarball(ifsdata_tarball, ifsdata_dir)

        # Update paths (which automatically verifies checksums)
        if verify_checksum:
            src_dir = [output_dir]
            if ifsdata_dir is not None:
                src_dir += [ifsdata_dir]
            obj.update_srcdir(
                src_dir, update_files=True, with_ifsdata=with_ifsdata or ifsdata_dir is not None
            )

        # Save (updated) YAML file in output_dir
        if tarballs:
            obj.to_yaml(output_dir / summary_file.name)
        elif ifsdata_tarball is not None:
            obj.to_yaml(ifsdata_dir / summary_file.name)

        return obj
