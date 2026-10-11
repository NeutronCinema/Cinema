import numpy as np
from Prompt.Analyser import DataLoader, IDFLoader, RunData, SampleData, Normalise, ErrorPropagator
from Prompt.Math.Hist import Hist1D, Hist2D, SpectrumEstimator, Est1D
from Prompt.Math import *
import matplotlib.pyplot as plt
import sys


# qehist = Est1D(0.443953, 100, 1000, False)
# qehist.fill(1, 1, 0.1)
# qehist.fill(1, 1, 0.1)
# qehist.plot(True)
# sys.exit()

def reduction(rundata, moduleName):
    idf = IDFLoader('idf')
    tree = idf.query(moduleName)

    mod2sample = 30000.
    sam2det = np.linalg.norm(tree.location, axis=1)
    mod2det = mod2sample + sam2det

    qehist = Est1D(0.443953, 100, 300, False)
    # for plxIdx in range(40,45):
    for plxIdx in range(rundata.detErrPro.weight.shape[0]):
        print(f'pixel ID {plxIdx} {rundata.detErrPro.weight.shape[0]}')
        speedAtPixel = mod2det[plxIdx]/rundata.tofCentre
        ekin = v2ekinMany(speedAtPixel)
        # plt.semilogy(ekin)
        # plt.show()
        pixelLocation = tree.location[plxIdx]
        # cosAngle = pixelLocation.dot(np.array([0.,0.,1.]))/sam2det[plxIdx]
        cosAngle = pixelLocation[2]/sam2det[plxIdx]
        print(f'mean scattering angle {np.arccos(cosAngle.mean())/(np.pi/180.)}')
        q = angleCosine2QMany(cosAngle, ekin, ekin)
        qehist.fillmany(q, rundata.detErrPro.weight[plxIdx, :], rundata.detErrPro.error[plxIdx, :])

    qe = qehist.getCentre()
    se = qehist.getWeight()

    return qe, se, qehist


# holder 17262, 17282
# V 17327
# d2o 17672

# moduleName = 'module10203'
# moduleName = 'module10504'
moduleName = 'module10701'

d2o = RunData('./RUN0017672/detector.nxs', moduleName, Normalise.byMonitor)
holder = RunData('./RUN0017262/detector.nxs', moduleName, Normalise.byMonitor)
v = RunData('./RUN0017327/detector.nxs', moduleName, Normalise.byMonitor)

d2o -= holder
v -= holder
# d2o.detErrPro.plot(True)
# sys.exit()


d2o_q, d2o_s, d2o_est = reduction(d2o, moduleName)
# plt.plot(d2o_q, d2o_s*d2o_q*d2o_q, label = f'D2O {moduleName}')

v_q, v_s, v_est = reduction(v, moduleName )
# plt.plot(v_q, v_s*v_q*v_q, label = f'V {moduleName}')

d2o_est.plot(label='D20')
v_est.plot( label='V')


plt.figure()
plt.plot(d2o_q, np.divide(d2o_s, v_s, where=v_s!=0.,
                          out=np.zeros_like(d2o_s, dtype=float)))

plt.figure()
errp = ErrorPropagator(d2o_est.getWeight(),  d2o_est.getCentre(), error = d2o_est.getError())
errp.divide(v_est.getWeight(),  v_est.getError(), v_est.getCentre())

errp.plot()
plt.ylim([-3,3])


# plt.figure()
# ratio = np.divide(d2o_s, v_s, where=(np.abs(v_s)>1e-40))
# plt.plot(d2o_q, ratio, label = f'{moduleName}')
# plt.ylim([-3,3])
# plt.grid()
# plt.legend()
plt.show()


pass
