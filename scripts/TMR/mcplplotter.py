import numpy as np
from mcpl import collect_stats
import matplotlib.pyplot as plt

def ekin2wl(ekin):

    return np.sqrt(0.081804209605330899 / ekin)

result = collect_stats("scorerkiller@guideEntry.mcpl.gz")
print(result.get("ekin").keys())
ekin = result.get("ekin").get("hist_bins")
scores = result.get("ekin").get("hist")

plt.step(ekin2wl(ekin[:-1] * 1.e6) ,scores)
# plt.xscale("log")
plt.yscale("log")
plt.show()