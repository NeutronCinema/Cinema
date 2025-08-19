#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.colors as colors
import h5py
import argparse
from Cinema.Prompt import plotStyle
import numpy as np
import pathlib

def get_figure(h5file, show=True, save=False):
    plt.legend()
    if show:
        plt.show()
    if save:
        plt.savefig(f'{h5file}.pdf')
    if not show and not save:
        raise ValueError("Nothing happens: plot does not showed and not saved.")

def load_txt(filepath):
    data = np.loadtxt(filepath)
    x = data[:,0]
    y = data[:,1]
    try:
        e = data[:,2]
        return x, y, e
    except Exception as e:
        print(f"Warning: errors in reading errorbars; {e}")
        print("Warning: all errorbars set to zeros(0)")
        return x, y, np.zeros(len(y))

def load_1dh5(filepath):
    h5f = h5py.File(f'{filepath}')

    if 'center' not in h5f:
        raise ValueError("May be not a Prompt h5 file.")

    x = h5f[f'center'][()]
    y = h5f[f'weight'][()]
    e = h5f[f'sdev'][()]
    return x, y, e

def plot1d(file : str, xlog=False , ilog=True, 
           err=False, save=False, show=True,
           xlabel='x', ylabel='y', title='title'):

    if file.endswith('.h5'):
        x,y,e = load_1dh5(file)
    elif file.endswith('.dat'):
        x,y,e = load_txt(file)
    else:
        raise ValueError(f"file not found at {file}")

    ilabel = f"{file}"
    if not err:
        try:
            plt.step(x[:-1], y, label=ilabel)
        except:
            plt.step(x, y, label=ilabel)
    else:
        plt.errorbar(x[:-1],y,e)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)

    if xlog:
        plt.xscale('log')
    if ilog:
        plt.yscale('log')
    

def plot2d(h5file, ilog=False , save=False, show=True,
           xlabel='x', ylabel='y', title='title'):

    h5f = h5py.File(f'{h5file}')

    if 'xcenter' not in h5f:
        raise ValueError("May be not a Prompt h5 file.")

    x = h5f[f'xcenter'][()]
    y = h5f[f'ycenter'][()]
    z = h5f[f'weight'][()]
    e = h5f[f'sdev'][()]
    X, Y = np.meshgrid(x, y)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)

    if ilog:
        pcm = ax.pcolormesh(X, Y, z.T, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=z.max()*1e-2, vmax=z.max()), shading='auto')
    else:
        pcm = ax.pcolormesh(X, Y, z.T, cmap=plt.cm.jet,shading='auto')
    fig.colorbar(pcm, ax=ax)

    
def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='+',type=str, help='Path of h5 file produced by Prompt simulations.')
    parser.add_argument('--save', action='store_true', help='save plot as pdf file.')
    parser.add_argument('--show', action='store_true', help='show plot.')
    parser.add_argument('--xlog', action='store_true', help='xlog scale.')
    parser.add_argument('--ilog', action='store_true', help='intensity plotted in logscale.')
    parser.add_argument('--xlabel', type=str, default='x', help='xlabel.')
    parser.add_argument('--ylabel', type=str, default='y', help='ylabel.')
    parser.add_argument('--title', type=str, default='title', help='title.')
    parser.add_argument('--err', action='store_true', help='err bar.')
    args = parser.parse_args()
    return args

def main():
    plotStyle()
    args = parse()

    for filepath in args.file:
        if filepath.endswith(".h5"):
            h5f = h5py.File(f'{filepath}')
            if 'xcenter' in h5f:
                plot2d(filepath, args.ilog, args.save, args.show, 
                    args.xlabel, args.ylabel, args.title)
            elif 'center' in h5f:
                plot1d(filepath, args.xlog, args.ilog, args.err, args.save, args.show, 
                    args.xlabel, args.ylabel, args.title)
            else:
                raise ValueError("May be not a Prompt h5 file.")
        elif filepath.endswith(".dat"):
                plot1d(filepath, args.xlog, args.ilog, args.err, args.save, args.show, 
                    args.xlabel, args.ylabel, args.title)
        else:
            raise ValueError("Not implemented")
    get_figure(filepath, args.show, args.save)
    
def main_dev():
    cwd = pathlib.Path.cwd()
    path = cwd / "iq.dat"
    load_txt(path)

if __name__ == '__main__':
    main()
    # main_dev()