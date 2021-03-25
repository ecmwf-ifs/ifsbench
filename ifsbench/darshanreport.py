"""
Darshan report parsing utilities.
"""
import io
import mmap
import subprocess
from contextlib import contextmanager
from pathlib import Path
import pandas as pd


__all__ = ['DarshanReport']


@contextmanager
def open_darshan_logfile(filepath):
    """
    Utility context manager to run darshan-parser on the fly if the given file
    path does not point to a darshan log text file.
    """
    filepath = Path(filepath)
    with filepath.open('r') as logfile:
        is_parser_log = logfile.readline().find('darshan log version:') != -1
    if is_parser_log:
        try:
            logfile = filepath.open('r')
            report = mmap.mmap(logfile.fileno(), 0, prot=mmap.PROT_READ)
            yield report
        finally:
            logfile.close()
    else:
        try:
            cmd = 'darshan-parser'
            result = subprocess.run([cmd, str(filepath)], capture_output=True, check=True)
            yield result.stdout
        finally:
            pass


class DarshanReport:
    """
    Utility reader to parse the output of `darshan-parser`.

    This exists for compatibility reasons to emulate the behaviour of
    pydarshan's `DarshanReport` for Darshan versions prior to 3.3.

    Parameters
    ----------
    filepath : str or :any:`pathlib.Path`
        The file name of the log file with the output from `darshan-parser` or
        the runtime logfile produced by Darshan. If the latter is given,
        `darshan-parser` will be called to parse this and create the text
        output before reading.
    """

    def __init__(self, filepath):
        with open_darshan_logfile(filepath) as report:
            self._parse_report(report)

    @staticmethod
    def _parse_key_values(report, start, end):
        pairs = {}
        for line in report[start:end].splitlines():
            line = line.decode()
            if not line.startswith('# ') or ': ' not in line:
                # skip empty/decorative lines
                continue
            key, value = line[1:].split(': ', maxsplit=1)
            key, value = key.strip(), value.strip()
            if key in pairs:
                pairs[key] = pairs[key] + ', ' + value
            else:
                pairs[key] = value
        return pairs

    def _parse_report(self, report):
        #report = report.decode()

        # Get log version
        ptr = report.find(b'darshan log version:')
        line_start = report.find(b'\n', ptr)
        self.version = report[ptr + len(b'darshan log version:'):line_start].strip()

        # Find output regions
        start_regions = report.find(b'log file regions')
        start_mounts = report.find(b'mounted file systems')
        start_columns = report.find(b'description of columns')

        # Find module outputs
        modules = []
        end = start_columns
        ptr = report.find(b' module data', end)
        while ptr != -1:
            start = report.rfind(b'\n#', 0, ptr)
            module_name = report[start+2:ptr].strip().decode()
            table_start = report.find(b'#<module>', ptr)
            end = report.find(b'\n\n', table_start)
            modules += [(module_name, start, table_start, end)]
            ptr = report.find(b' module data', end)

        # Parse key-value regions
        self.header = self._parse_key_values(report, 0, start_regions)
        self.logfile_regions = self._parse_key_values(report, start_regions, start_mounts)
        self.file_systems = self._parse_key_values(report, start_mounts, start_columns)
        self.columns = self._parse_key_values(report, start_columns, modules[0][1])

        # Parse modules
        self._records = {}
        self._name_records = {}
        for module, start, table_start, end in modules:
            desc_start = report.find(b'description of', start)
            self._name_records[module] = self._parse_key_values(report, desc_start, table_start)
            module_record = io.StringIO(report[table_start:end].decode())
            self._records[module] = pd.read_csv(module_record, sep='\t', index_col=False)

    @property
    def records(self):
        """
        Return a `dict` of :any:`pandas.DataFrame` containing all records.

        See the `documentation of darshan-parser output
        <https://www.mcs.anl.gov/research/projects/darshan/docs/darshan-util.html#_guide_to_darshan_parser_output>`_
        for available modules and the meaning of record fields.

        Returns
        -------
        `dict` of `pandas.DataFrame`
            Dictionary of module name to DataFrame mappings.
        """
        return self._records

    @property
    def name_records(self):
        """
        Return a `dict` of columns names and their descriptions for each module.

        Returns
        -------
        `dict` of `dict`
            Column descriptions for each module.
        """
        return self._name_records
