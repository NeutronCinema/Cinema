#!/usr/bin/env python3

import numpy as np
from scripts.sans.sans_model import sans_run

import multiprocessing

numNeutron = 1e7
# thickness = np.linspace(0.1, 10, 3)
thickness = np.array([0.5,2,5,10])
detpos = np.linspace(1100, 25000, 30)
divergence = np.linspace(0, 5, 30)
wl = np.linspace(1, 6, 5)
var = thickness

def process(x):
    sim, sqw, sqRaw = sans_run(3, numNeutron, x, 6000, 0)
    qq = sqw.getCentre()[0]
    sq = sqw.getWeight().sum(1)/sqw.getAccWeight()

    qq1d = sqRaw.getEdge()[:-1]
    sq1d = sqRaw.getWeight()/sqRaw.getAccWeight()
    sim.clear()
    return (qq1d, sq1d)

# for t in x1:
#     sim, yy = sans_run(1,numNeutron,t)
#     sim.clear()
#     y.append(yy)

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    fig, (intensity,ratio) = plt.subplots(2,1,sharex=True,height_ratios=[2,1])
    with multiprocessing.Pool() as pool:
        sq = pool.map(process, var)
        zzip = list(zip(sq,var))
        base = zzip.pop(0)
        plt.xlabel('Q')
        intensity.set_ylabel('Relative intensity')
        ratio.set_ylabel('Ratio')
        fig.suptitle('Intensity relative to sample thickness(t) = 0.1')
        plt.xscale("log")
        marker = ['+-', 'x-', '*-']
        im = 0
        for sqresult, v in zzip:
            intensity.plot(sqresult[0], sqresult[1], marker[im], ms=4, label=f't={int(v)}mm')
            ratio.step(sqresult[0], (sqresult[1]-base[0][1])/base[0][1]*100)
            im += 1
        intensity.legend()
        # plt.yscale("log")
        ratio.set_yticks([-100,-50,0,50,100])
        plt.savefig('thickness.pdf')