#!/usr/bin/env python3

import numpy as np
from botorch_sans import sans_run

import multiprocessing

numNeutron = 1e5
# thickness = np.linspace(0.1, 10, 3)
thickness = np.array([0.1,2,5,10])
detpos = np.linspace(1100, 25000, 30)
divergence = np.linspace(0, 5, 30)
wl = np.linspace(1, 6, 5)
var = thickness

def process(x):
    sim, sqw = sans_run(3, numNeutron, x, 6000, 0)
    qq = sqw.getCentre()[0]
    sq = sqw.getWeight().sum(1)/sqw.getAccWeight()
    sim.clear()
    return (qq,sq)

# for t in x1:
#     sim, yy = sans_run(1,numNeutron,t)
#     sim.clear()
#     y.append(yy)

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    plt.figure(0)
    with multiprocessing.Pool() as pool:
        sqw = pool.map(process, var)
        zzip = list(zip(sqw,var))
        base = zzip.pop(0)
        for sqw_s, v in zzip:
            plt.plot(sqw_s[0], sqw_s[1]/base[0][1], label=f't={v}')
        plt.legend()
        plt.xlabel('Q')
        plt.ylabel('%')
        plt.title('Intensity ratio relative to sample thickness(t) = 0.1')
        plt.xscale("log")
        plt.savefig('thickness.pdf')