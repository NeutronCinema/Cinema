#!/usr/bin/env python3

from io import BytesIO
import numpy as np
from  Cinema.Prompt.histogram import Hist1D, NumpyHist1D
import matplotlib.pyplot as plt


def test_simulation():
    xbin=10
    xmin=0.
    xmax=1.

    def create():
        histcpp=Hist1D(xmin, xmax, xbin)
        histpy=NumpyHist1D(xbin, [xmin, xmax])

        for i in range(10):
            data=np.random.random([2,10000])
            histpy.fill(data[0], data[1])
            histcpp.fillmany(data[0], data[1])

        np.testing.assert_allclose(histpy.hist, histcpp.getWeight(), rtol=1e-13, atol=1e-13)
        return histpy, histcpp

    hpy1, hpc1 = create()
    hpy2, hpc2 = create()

    hpc1.merge(hpc2)
    np.testing.assert_allclose(hpy1.hist+hpy2.hist, hpc1.getWeight(), rtol=1e-13, atol=1e-13)
    print('passed!')
