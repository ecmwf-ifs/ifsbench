# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from ifsbench.logging import debug


__all__ = ['GroupedBarPlot', 'StackedBarPlot']


class GroupedBarPlot:
    """
    A grouped bar plot that clusters individual bars by groups.

    Parameters
    ----------
    groups : list of str
        Names of the groups by which to cluster bars.
    """

    def __init__(self, groups):
        self.groups = groups
        self.x = np.arange(len(self.groups))

        self.fig, self.ax = plt.subplots(layout='constrained')
        self.width = 1. / len(self.groups)

        self.idx = 0

    def add_group(self, values, label):
        """
        Add a bar to each group for a given set of values.

        Parameters
        ----------
        values : list of float
            Values for the bar height for all group entries.
        label : str
            Label to appear in the legend for all entries
        """
        assert len(values) == len(self.groups)

        offset = self.width * self.idx
        rects = self.ax.bar(self.x + offset, values, self.width, label=label)
        self.ax.bar_label(rects, padding=3)

        self.idx += 1

    def plot(self, filename, title=None, ylabel=None, ylim=None):
        """
        Plot figure to file and configure labels and legends.

        Parameters
        ----------
        filename : str
            Path and name of output file.
        title : str, optional
            A title to add to the top of the plot.
        ylabel : str, optional
            Label for the y-axis
        ylim : tuple of float, optional
            Min and max value for the y-axis
        """
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.set_xticks(self.x + self.width, self.groups)
        self.ax.legend(loc='upper left', ncols=3)
        self.ax.set_ylim(ylim)

        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)


class StackedBarPlot:
    """
    A stacked bar plot that clusters multiple bars in a stack for each x-entry.

    Parameters
    ----------
    groups : list of str
        Names of the groups by which to cluster bars.
    cmap : str, optional
        Name of the colormap to use, as defined in matplotlib.
    """

    def __init__(self, groups, cmap='viridis'):
        self.groups = groups

        self.fig, self.ax = plt.subplots()

        # Define and discretise colormap
        self.cmap = mpl.colormaps[cmap]
        self.colors = self.cmap(np.linspace(0, 1, len(groups)))

    def add_stack(self, values, label):
        """
        Add stacked bar data for defined groups from a single run.

        Parameters
        ----------
        values : list of float
            The run time values to stack for each bar column
        label : str
            Label for the x-axis of this entry
        """
        assert len(values) == len(self.groups)

        total = 0.
        for i, v in enumerate(values):
            plt.bar(label, v, bottom=total, label=self.groups[i], color=self.colors[i])
            total += v

    def plot(self, filename, title=None, ylabel=None, ylim=None):
        """
        Plot figure to file and configure labels and legends.

        Parameters
        ----------
        filename : str
            Path and name of output file.
        title : str, optional
            A title to add to the top of the plot.
        ylabel : str, optional
            Label for the y-axis
        ylim : tuple of float, optional
            Min and max value for the y-axis
        """
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.legend(self.groups, loc='best')
        self.ax.set_ylim(ylim)

        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
