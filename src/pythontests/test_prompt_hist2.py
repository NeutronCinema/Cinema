#!/usr/bin/env python3

from io import BytesIO
import numpy as np
from  Cinema.Prompt.histogram import Hist2D, NumpyHist2D

import matplotlib.pyplot as plt


def test_simulation():
    xbin=10
    xmin=0.
    xmax=1.

    ybin=100
    ymin=0.
    ymax=1.

    #NumpyHist2D is an slow python implement, only use in the unittest
    hist=NumpyHist2D(xbin, ybin, [[xmin, xmax], [ymin, ymax]])
    histcpp=Hist2D(xmin, xmax, xbin, ymin, ymax, ybin)

    for i in range(100):
        data=np.random.random([2, 10000])
        hist.fill(data[0], data[1])
        histcpp.fillmany(data[0], data[1])

    np.testing.assert_array_equal(hist.hist, histcpp.getWeight())

    #test merge
    hist1=Hist2D(0, 1, 10, 0, 1, 10)
    hist1.fill(0.1, 0.1)
    print(hist1.getHit())

    hist2=Hist2D(0, 1, 10, 0, 1, 10)
    hist2.fill(0.2, 0.2)
    print(hist2.getHit())

    hist1.merge(hist2)
    print(hist1.getHit())

    ref=np.zeros([10,10])
    ref[1,1]=1
    ref[2,2]=1
    np.testing.assert_array_equal(hist1.getHit(), ref)

    # import copy
    # hist3=copy.copy(hist1)
    # hist3.merge(hist2)

    print('passed')
