# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from functools import cached_property
import re
from typing import Dict, List, Union

import pandas as pd

from ifsbench.serialisation_mixin import SerialisationMixin
from ifsbench.pydantic_utils import PydanticDataFrame

__all__ = ["AVAILABLE_BASIC_STATS", "EnsembleStats"]


# Statistics keywords available when calling calc_stats. In addition
# percentiles are supported with format '[p,P](\d{1,2})'.
AVAILABLE_BASIC_STATS = ["min", "max", "mean", "median", "sum", "std"]


class EnsembleStats(SerialisationMixin):
    """Reads, writes, summarises results across ensemble members."""

    frames: List[PydanticDataFrame]

    @cached_property
    def group(self):
        dfc = pd.concat(self.frames)
        return dfc.groupby(dfc.index)

    def calc_stats(self, stats: Union[str, List[str]]) -> Dict[str, pd.DataFrame]:
        """Calculate statistics.

        Desired statistics can be specified as a single string, e.g. 'mean', 'min',
        or as a list of strings. Supported stats are given by AVAILABLE_BASIC_STATS;
        in addition, percentiles between 0 and 100 can be specified as 'P10', 'p85', etc.

        Args:
            stats: string representation or list or string representations of stats values
                to be calculated.
        Returns:
            Dictionary or results with requested stat string representations as key and
                dataframes of results for that stat as value.
        """

        def std(x):
            # pandas uses sample standard deviation, we want population std.
            # Using function rather than lambda for the correct column name.
            return x.std(ddof=0)

        def _percentile(stat_name: str, nth: float):
            def _qtile(data):
                return data.quantile(nth / 100.0)

            _qtile.__name__ = stat_name
            return _qtile

        if isinstance(stats, str):
            stats = [stats]
        to_request = []
        for stat in stats:
            percentile_check = re.match(r"[p,P](\d{1,3})$", stat)
            if percentile_check:
                ptile_value = int(percentile_check.group(1))
                if ptile_value > 100:
                    raise ValueError(
                        f"Percentile has to be in [0, 100], got {ptile_value}."
                    )
                to_request.append(_percentile(stat, ptile_value))
            elif stat == "std":
                to_request.append(std)
            elif stat in AVAILABLE_BASIC_STATS:
                to_request.append(stat)
            else:
                raise ValueError(
                    f"Unknown stat: {stat}. Supported: {AVAILABLE_BASIC_STATS} and percentiles (e.g. p85)."
                )
        df = self.group.agg(to_request)
        return {stat: df.xs(stat, level=1, axis=1) for stat in stats}
