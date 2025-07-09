"""
Plotting utilities for GtaModel tools.

"""

import matplotlib.pyplot as plt
from os import PathLike
import numpy as np
import pandas as pd
from typing import Tuple

idx = pd.IndexSlice

def plot_line_profiles(
        line_profiles: pd.DataFrame,
        fp: PathLike,
        *,
        figsize: Tuple=(8, 10),
        fontsize: float=12.0,
        titlefontsize: float=16.0
    ) -> None:
    """ Plots transit volumes, boardings and alightings along line profile.

    Args:
        line_profiles:
            Produced from Network.calculate_line_profiles_from_config
        fp:
            Filepath for exported image.
        figsize: tuple(float) 
            Width and height of individual profile plot. Default is (8, 10)
        fontsize 
            font size of tick labels and legend text
        titlefontsize
            font size of title
    """

    # Find the number of transit lines (# rows in the plot)
    lines = line_profiles.index.get_level_values('Line').unique()
    nrows = len(lines)
    # Find maximum number of directions per line (# columns in plot)
    ncols = 0
    for line in lines:
        line_df = line_profiles.loc[idx[line, :]]
        ndirs_in_line = line_df.index.get_level_values('Direction').nunique()
        if ndirs_in_line > ncols:
            ncols = ndirs_in_line
    figsize = (ncols*figsize[0], nrows*figsize[1])

    # Create the plot
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize, layout='constrained')
    for i, line in enumerate(lines):
        line_df = line_profiles.loc[idx[line, :]]
        # Loop over all directions in the line
        for j, direction in enumerate(
                line_df.index.get_level_values('Direction').unique()):
            line_dir = line_df.loc[direction].copy()
            nstns = len(line_dir)
            # Check for a two-level index, means that there's a loop.
            if line_dir.index.nlevels==2:
                combined_index = \
                    line_dir.index.get_level_values(0).astype(str).str.cat(
                        line_dir.index.get_level_values(1).astype(str), 
                        sep=' - '
                    )
                line_dir = line_dir.set_index(combined_index)
            ax = axs[i, j]
            ax.set_title(
                f'Line profile:\n{line}\n{direction}', 
                fontsize=titlefontsize
            )
            # Boardings 
            ax.plot(
                line_dir.index.astype(str), line_dir['boardings'], linestyle='', 
                fillstyle='full', marker = '^', markerfacecolor ='cyan',
                markeredgecolor='black', markeredgewidth=1, markersize=7,
                label='Boardings'
            )
            # Alightings 
            ax.plot(
                line_dir.index.astype(str), line_dir['alightings'], linestyle='', 
                fillstyle='full', marker = 'v', markerfacecolor ='blue',
                markeredgecolor='black', markeredgewidth=1, markersize=7,
                label='Alightings'
            )
            # Volumes 
            ax.bar(
                line_dir.index.astype(str), line_dir['volume'], width=1, 
                color='blanchedalmond', edgecolor='black', linewidth=1,
                label='Volume'
            )
            
            # Write x labels
            major_ticks = np.arange(0, nstns)
            ax.set_xticks(major_ticks)
            xlabels = [''] * nstns
            stn_label_incr = max(int(nstns // 10), 1)
            for xpos, tick in enumerate(ax.xaxis.get_majorticklabels()):
                if xpos % stn_label_incr == 0:
                    xlabels[xpos] = line_dir.index[xpos]
                tick.set_horizontalalignment("right")
            ax.set_xticklabels(xlabels)
            ax.tick_params('x', rotation=45, labelsize=fontsize)
            ax.tick_params('y', labelsize=fontsize)
            
            ax.legend(loc=1, fontsize=fontsize)

    fig.savefig(fp)
    fig.clf()


def plot_tlfds(fp, *args):
    """ Plot an number of trip length distributions.

    Args:
        fp: Filepath in which to save final plot
        args:
            Set of four inputs, each containing:
            - numpy array: cumulative number of trips
            - numpy array: bins
            - str: label
            - matplotlib color
    """
    len_args = len(args)
    if len_args == 0 or len_args % 4 != 0:
        raise ValueError(
            '*args must contain inputs in sets of four, as follows: \n'
            '  - cumulative number of trips \n'
            '  - bin edges \n'
            '  - label \n'
            '  - matplotlib color \n'
        )
    fig, ax = plt.subplots(layout='constrained')

    n_series = int(len_args // 2)
    all_bins = []
    for i in range(0, n_series, 4):
        v = list(args[i])
        bins=list(args[i+1])
        label = args[i+2]
        color = args[i+3]
        
        x = [bins[0]]
        y = [0]
        for j in range(0, len(v)):
            x.extend([bins[j], bins[j+1]])
            y.extend([v[j], v[j]])
        ax.plot(x, y, label=label, color=color)
        all_bins.extend(bins)

    all_bins = np.sort(np.unique(all_bins))
    ymin, ymax = ax.get_ylim()
    xmin, xmax = ax.get_xlim()
    # Draw outer box around limits
    ax.plot([0, 0], [0, ymax], color='k', linewidth=2)
    ax.plot([xmax, xmax], [0, ymax], color='k', linewidth=2)
    ax.plot([0, xmax], [0, 0], color='k', linewidth=2)
    ax.plot([0, xmax], [ymax, ymax], color='k', linewidth=2)
    # Draw dotted lines at bin edges
    for ab in all_bins:
        if ab > 0 and ab < xmax:
            ax.plot([ab, ab], [0, ymax], color='k', linestyle=':',
                   linewidth=0.5)
    ax.legend(loc='upper center')
    
    fig.savefig(fp)
    fig.clf()