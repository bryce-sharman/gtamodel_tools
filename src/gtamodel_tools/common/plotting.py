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
