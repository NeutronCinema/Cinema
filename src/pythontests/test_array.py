import numpy as np
from  Cinema.Prompt.histogram import Hist1D, NumpyHist1D
import matplotlib.pyplot as plt
from Cinema.Interface import CinemaArray, CinemaXY

xbin=10
xmin=0.
xmax=1.

histcpp=Hist1D(xmin, xmax, xbin)
for i in range(10):
    data=np.random.random([2,10000])
    histcpp.fillmany(data[0], data[1])


# ca = CinemaXY.from_sdev(histcpp.getWeight(), histcpp.getSdev(), histcpp.getCentre()) 

data = CinemaXY.from_hist1d(histcpp)

data = data*2
np.testing.assert_allclose(data.mean , histcpp.getWeight()*2, rtol=1e-13, atol=1e-13)
np.testing.assert_allclose(data.sdev , histcpp.getSdev()*2, rtol=1e-13, atol=1e-13)
np.testing.assert_allclose(data.x , histcpp.getCentre(), rtol=1e-13, atol=1e-13)

print('passed!')


# histcpp.plot(False)
# plt.figure()
# data.plot()
# plt.show()
