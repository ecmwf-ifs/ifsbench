# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pandas as pd
from pathlib import Path
import xml.etree.ElementTree as ET
import ast

__all__ = ['GStatsRecord']

def as_float(element):
    #If you expect None to be passed:
    try:
        float(element)
        return ast.literal_eval(element)
    except ValueError:
        return element

def extract_table_with_pandas(file_path, start_marker=None, end_marker=None):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    counter = 0
    # Optionally extract only the part between start and end markers
    if start_marker and end_marker:
        in_table = False
        table_lines = []
        for line in lines:
            if start_marker in line:
                in_table = True
                continue
            if end_marker in line:
                break
            if in_table:
                if counter == 0:
                    header = line
                else:
                    table_lines.append(line)
                counter += 1
    else:
        table_lines = lines

    spans = [(0, 4), (5, 48), (49, 54), (55, 68), (69, 82), (83, 92), (93, -1)]
    # Split lines into columns using regex (e.g., multiple spaces or tabs)

    header_str = [header[span[0]:span[1]].strip().lower().replace('(ms)', '').replace('(%)', '') for span in spans]

    rows = []
    for line in table_lines:
        columns = [as_float(line[span[0]:span[1]].strip()) for span in spans]
        if columns:
            rows.append(columns)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=header_str)

    return df

class GStatsRecord:
    """
    Class to encapsulate a GStats performance record for a single benchmark run.
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        path_xml = path/'gstats.xml' if path.is_dir() else path
        if path.is_dir():
            path_node_files = list(path.glob('NODE.*'))
            path_node = path_node_files[0] if path_node_files else path
        else:
            path_node = path
        if path_xml.is_file():
            df = pd.read_xml(path_xml, xpath='*/item', parser='etree')
            df = df.set_index('id')
        elif path_node.is_file():
            df = extract_table_with_pandas(path_node, start_marker='STATS FOR ALL TASKS', end_marker='TOTAL MEASURED IMBALANCE')
            df = df.set_index('num')
        else:
            raise FileNotFoundError
        return cls(data=df)

    def total_time(self, gid):
        """ Cumulative total time in seconds for a given GStats-ID """
        try:
            return self.data.at[gid, 'mean'] * self.data.at[gid, 'calls'] / 1000.
        except Exception:
            return 0

    @property
    def total_time_execution(self):
        """ Cumulative total time in seconds for a given GStats-ID """
        return self.total_time(gid=0)


    @property
    def total_time_steps(self):
        """ Total time spent in forward integration time steps """
        return self.total_time(gid=1)  # CNT4     - FORWARD INTEGRATION

    @property
    def total_io(self):
        """ Total time spent in IO"""
        t = self.total_time(gid=11) # IOPACK
        t += self.total_time(gid=17) # GRIDFPOS
        t += self.total_time(gid=29) # SU4FPOS
        t += self.total_time(gid=30) # DYNFPOS
        t += self.total_time(gid=31) # POSDDH
        t += self.total_time(gid=25) # SPECRT
        return t

    @property
    def total_trans(self):
        """ Total time spent in spectral transforms """
        t = self.total_time(gid=102)  # LTINV_CTL   - INVERSE LEGENDRE TRANSFORM
        t += self.total_time(gid=103)  # LTDIR_CTL   - DIRECT LEGENDRE TRANSFORM
        t += self.total_time(gid=106)  # FTDIR_CTL   - DIRECT FOURIER TRANSFORM
        t += self.total_time(gid=107)  # FTINV_CTL   - INVERSE FOURIER TRANSFORM
        t += self.total_time(gid=152)  # LTINV_CTL   - M TO L TRANSPOSITION
        t += self.total_time(gid=153)  # LTDIR_CTL   - L TO M TRANSPOSITION
        t += self.total_time(gid=157)  # FTINV_CTL   - L TO G TRANSPOSITION
        t += self.total_time(gid=158)  # FTDIR_CTL   - G TO L TRANSPOSITION
        return t

    @property
    def total_ecphys(self):
        """ Total time spent in ECMWF physics package (EC_PHYS) """
        return self.total_time(gid=6)  # SCAN2M - EC_PHYS

    @property
    def total_gp_dynamics(self):
        """ Total time spent in grid-point dynamics (CPG) """
        return self.total_time(gid=8)  # SCAN2M - GRID-POINT DYNAMICS

    @property
    def total_radiation(self):
        """ Total time spent in radiation """
        return self.total_time(gid=13)  # SCAN2M - GRID-POINT DYNAMICS

    @property
    def total_semi_lag(self):
        """ Total time spent in semi-lagrangian """
        t = self.total_time(gid=37)  # CPGLAG - SL COMPUTATIONS
        t += self.total_time(gid=51)  # SCAN2M - SL COMM. PART 1
        t += self.total_time(gid=89)  # SCAN2M - SL COMM. PART 2
        return t

    @property
    def total_wave(self):
        """ Total time spent in wave model (WAM) """
        return self.total_time(gid=38)  # WAM      - TOTAL COST OF WAVE MODEL
