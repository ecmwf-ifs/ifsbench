# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from collections import OrderedDict
from collections.abc import Iterable
from enum import Enum, unique
import re
import pandas as pd

from ifsbench.logging import debug

__all__ = ['DrHook', 'DrHookRecord']


@unique
class DrHook(Enum):
    """
    Enum class to provide environment presets for different DrHook modes.
    """

    OFF = 0
    PROF = 1

    __env_map__ = {
        OFF : {
            'DR_HOOK': '0',
        },
        PROF : {
            'DR_HOOK': '1',
            'DR_HOOK_IGNORE_SIGNALS': '0',
            # 'DR_HOOK_USE_LOCKFILE': '0',
            'DR_HOOK_OPT': 'prof',
        }
    }

    @property
    def env(self):
        return self.__class__.__env_map__[self.value]


class DrHookRecord:
    """
    Class to encapsulate a DrHook performance record for a single benchmark run.
    """
    sre_number = r'[\w\-\+\.]+'
    sre_tag = r'[\w\(\)\*_-@]+'

    re_program = re.compile(r"program='(?P<program>.*)'")
    re_walltime = re.compile(fr'Wall-time is (?P<walltime>{sre_number}) sec on proc#{sre_number} '
                             fr'\((?P<nprocs>{sre_number}) procs, (?P<threads>{sre_number}) threads\)')
    re_memory = re.compile(fr'Memory usage : {sre_number} MB (heap), {sre_number} MB (rss), '
                           fr'{sre_number} MB (stack), {sre_number} MB (vmpeak), {sre_number} (paging)')
    re_row = re.compile(fr'(?P<id>{sre_number}) +(?P<percent>{sre_number}) +(?P<cumul>{sre_number}) +'
                        fr'(?P<self>{sre_number}) +(?P<total>{sre_number}) +(?P<calls>{sre_number}) +'
                        fr'{sre_number} +{sre_number} +(?P<routine>.*)')

    def __init__(self, data, metadata):
        self.data = data
        self.metadata = metadata

    def to_dict(self, orient='index'):
        """
        Return content of this `RunRecord` as a single Python dictionary.
        """
        d = OrderedDict()
        d['metadata'] = self.metadata.to_dict(orient=orient)
        d['data'] = self.data.to_dict(orient=orient)
        return d

    def pprint(self):
        """
        Pretty-print content of the merged DrHook results.
        """
        s =  f'The name of the executable : {self.metadata["program"]}\n'
        s += f'Number of MPI-tasks        : {self.metadata["nprocs"]}\n'
        s += f'Number of OpenMP-threads   : {self.metadata["threads"]}\n'
        s += f'Wall-times over {self.metadata["nprocs"]:.3f} MPI-tasks (secs) : '
        s += f'Min={self.metadata["mintime"]:.3f}, Max={self.metadata["maxtime"]:.3f}, '
        s += f'Avg={self.metadata["avgtime"]:.3f}, StDev={self.metadata["stdtime"]:.3f}\n'
        s += 'Routines whose total time (i.e. sum) > 0.010 secs will be included in the listing\n'
        s += '  Avg-%   Avg.time   Min.time   Max.time   St.dev  Imbal-%   # of calls : Name of the routine\n'
        for _, row in self.data.iterrows():
            s += f' {row["avgPercent"]:6.2f}%    {row["avgTime"]:6.3f}    {row["minTime"]:6.3f}    '
            s += f'{row["maxTime"]:6.3f}    {row["stddev"]:6.3f}    {row["imbalance"]:6.2f}    '
            s += f'{row["numCalls"]:9.d} : {row["routine"]}\n'
            return s

    def write(self, filepath):
        """
        Write an aggregated benchmark result to file
        """
        filepath = Path(filepath)
        self.data.to_csv(filepath.with_suffix('.drhook.csv'))
        self.metadata.to_csv(filepath.with_suffix('.drhook.meta.csv'))

        # Pretty print a total for human consumption
        with filepath.with_suffix('.drhook.txt').open('w', encoding='utf-8') as f:
            f.write(self.pprint())

    @classmethod
    def from_dict(cls, data, metadata, orient='index'):
        """
        Load DrHook output from dumped dictionaries into :any:`pandas.DataFrame`
        """
        return DrHookRecord(data=pd.DataFrame.from_dict(data, orient=orient),
                            metadata=pd.DataFrame.from_dict(metadata, orient=orient))

    @classmethod
    def from_raw(cls, filepath):
        """
        Load raw drhook output and aggregate into merged performance record
        """
        filepath = Path(filepath)
        filepath = filepath/'drhook.*' if filepath.is_dir() else filepath
        data, metadata = cls.parse_profiles(filepath)
        return DrHookRecord(data, metadata)

    @classmethod
    def from_file(cls, filepath):
        """
        Load a stored aggregated benchmark result from file
        """
        filepath = Path(filepath)
        data = pd.read_csv(filepath.with_suffix('.csv'), float_precision='round_trip')
        metadata = pd.read_csv(filepath.with_suffix('.meta.csv'), float_precision='round_trip')
        return DrHookRecord(data, metadata)

    @classmethod
    def parse_profiles(cls, filepath):
        """
        Parse the raw DrHook (per-process) profile files into a :any:`pandas.DataFrame`.
        """
        debug(f'Parsing DrHook profile: {filepath}')

        filepath = Path(filepath)
        columns = ['id', 'percent', 'cumul', 'self', 'total', 'calls', 'routine']

        dfs = []
        metas = []
        for path in filepath.parent.glob(filepath.name):
            with Path(path).open('r', encoding='utf-8') as f:
                raw = f.read()

            # Parse metadata into series object
            # m = [m.groupdict() for m in cls.re_walltime.finditer(raw)]
            m = cls.re_program.search(raw).groupdict()
            m.update(cls.re_walltime.search(raw).groupdict())
            # m_memory = cls.re_walltime.search(raw)
            # m.update(m_memory if m_memory else {}}
            metas += [pd.Series(m).to_frame().transpose()]

            rows = [m.groups() for m in cls.re_row.finditer(raw)]
            df = pd.DataFrame(rows, columns=columns)
            df.set_index('id', inplace=True)

            # Extract the thread ID into individual column and drop '*'
            df['thread'] = df['routine'].apply(lambda n: int(n.split('@')[-1].split(':')[0]))
            df['routine'] = df['routine'].apply(lambda n: n.split('@')[0].replace('*', ''))
            dfs += [df]

        # Concatenate all DrHook profiles
        data = pd.concat(dfs)
        meta = pd.concat(metas)

        # Provide across process statistics for metadata
        meta['walltime'] = pd.to_numeric(meta['walltime'], errors='coerce')
        meta['mintime'] = meta['walltime'].min()
        meta['maxtime'] = meta['walltime'].max()
        meta['avgtime'] = meta['walltime'].mean()
        meta['stdtime'] = meta['walltime'].std()

        meta.drop(['walltime'], axis=1, inplace=True)
        meta.drop_duplicates(inplace=True)

        # Clean up and sanity check values
        data['percent'] = pd.to_numeric(data['percent'].fillna(0), errors='coerce')
        data['cumul'] = pd.to_numeric(data['cumul'].fillna(0), errors='coerce')
        data['self'] = pd.to_numeric(data['self'].fillna(0), errors='coerce')
        data['total'] = pd.to_numeric(data['total'].fillna(0), errors='coerce')
        data['calls'] = pd.to_numeric(data['calls'].fillna(0), errors='coerce')

        # Normalize statistics across processes and threads
        grp = data.groupby(['routine'])
        data['avgPercent'] = grp['percent'].transform('mean')
        data['avgTime'] = grp['self'].transform('mean')
        data['minTime'] = grp['self'].transform('min')
        data['maxTime'] = grp['self'].transform('max')
        data['stddev'] = grp['self'].transform('std')
        data['avgTimeTotal'] = grp['total'].transform('mean')
        data['minTimeTotal'] = grp['total'].transform('min')
        data['maxTimeTotal'] = grp['total'].transform('max')
        data['numCalls'] = grp['calls'].transform('sum')
        data['cumulative'] = grp['cumul'].transform('max')
        data['thread'] = grp['thread'].transform('max')

        # Drop raw per-process/thread values and compute imbalance
        data.drop(['percent', 'self', 'total', 'cumul', 'calls'], axis=1, inplace=True)
        data.drop_duplicates(inplace=True)
        data['imbalance'] = (data['maxTime'] - data['minTime']) / data['maxTime'] * 100

        return data, meta

    def get(self, routine, metric='avgTimeTotal', fill=None):
        """
        Extract timing values for one or more specific routines.

        Parameters
        ----------
        routine : str or list of str
            Single of list of subroutine names for which to extract values.
        metric : str
            Name of the measurement metric for which to extract values.
        fill : any, optional
            Fill value to use for missing result entries
        """
        if isinstance(routine, Iterable) and not isinstance(routine, str):
            # Extract a list of entries if an iterable of keys is given
            result = [self.data.loc[self.data['routine'] == r][metric] for r in routine]
            return [fill if r.empty else r.iloc[0] for r in result]

        result = self.data.loc[self.data['routine'] == routine][metric]
        return fill if result.empty else result.iloc[0]
