#!/usr/bin/env python3

import numpy as np
from botorch_sans import sans_run

numNeutron = 1e6
x1 = np.linspace(1e-1, 10, 20)
y = []
for t in x1:
    sim, yy = sans_run(1,numNeutron,t)
    sim.clear()
    y.append(yy)

result = np.vstack((x1, np.array(y)))
print(result)
np.savetxt('data.csv', result.T, delimiter=',')