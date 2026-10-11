import numpy as np
from yn_ana_code import SQTrueHist, MultiScatAnalysor, atomNum, SQHist
from Cinema.Experiment.Analyser.DataLoader import ErrorPropagator
from Cinema.Interface import plotStyle
import matplotlib.pyplot as plt
import os

# Root of the simulated-output tree for this analysis: point
# CINEMA_MPI2022_RUNDATA at it; when unset, fall back to the run-relative
# default with a warning.
data_root = os.environ.get('CINEMA_MPI2022_RUNDATA')
if not data_root:
    print('Warning: CINEMA_MPI2022_RUNDATA is not set - falling back to the '
          "relative default 'cinemaRunData/2022_8_7'")
    data_root = 'cinemaRunData/2022_8_7'

# example for analyzing sqtrue of d2o in 1Dhist
numNeutron = 3.4e+10
d2o_atomNum, v_atomNum = atomNum(d2o_r=1.0, d2o_h=14.3376, v_r=1.0, v_h=60.0)
d2o = SQTrueHist(os.path.join(data_root, 'HW_D_1_NumBig/HW_R1/*ScororDeltaMomentum_SofQ_He_seed*.h5'))
d2o_qtrue, d2o_s, d2o_err = d2o.fillHist(1, 85, xmin=0.1, xmax=120.0, numbin=150, linear=False)

v = SQTrueHist(os.path.join(data_root, 'HW_D_1_NumBig/V_R1/*ScororDeltaMomentum_SofQ_He_seed*.h5'))
v_qtrue, v_s, v_err = v.fillHist(1, 85, xmin=0.1, xmax=120.0, numbin=150, linear=False)

# d2o_calibration and error_propagate
d2o_calib = ErrorPropagator(d2o_s/d2o_atomNum/numNeutron,  d2o_qtrue, error=d2o_err/d2o_atomNum/numNeutron)
d2o_calib.divide(v_s/v_atomNum/numNeutron,  v_err/v_atomNum/numNeutron, v_qtrue)
d2o_s_calib = d2o_calib.weight
d2o_s_calib_err = d2o_calib.error*d2o_calib.weight

# example for decomposing sqtrue of d2o in 1Dhist
# d2oMS = MultiScatAnalysor(os.path.join(data_root, 'HW_D_1_NumBig/HW_R1/*ScororDeltaMomentum_SofQ_He_seed*.h5'))
# d2oMS1_qtrue, d2oMS1_s, d2oMS1_err = d2oMS.sqHist(1, 85, xmin=0.1, xmax=120.0, numbin=150, scatnum=1, inelastic=True, linear=False)
# d2oMS1_calib = ErrorPropagator(d2oMS1_s/d2o_atomNum/numNeutron,  d2oMS1_qtrue, error=d2oMS1_err/d2o_atomNum/numNeutron)
# d2oMS1_calib.divide(v_s/v_atomNum/numNeutron,  v_err/v_atomNum/numNeutron, v_qtrue)
# d2oMS1_s_calib = d2oMS1_calib.weight
# d2oMS1_s_calib_err = d2oMS1_calib.error*d2oMS1_calib.weight

# plot
plotStyle()
plt.xlim(0.0, 16.0)
plt.ylim(0.0, 6.0)
plt.errorbar(d2o_qtrue, d2o_s_calib , yerr=d2o_s_calib_err, fmt='o-', label='R_D$_2$O=1mm, b=1, Total')
# plt.errorbar(d2oMS1_qtrue, d2oMS1_s_calib , yerr=d2oMS1_s_calib_err, fmt='o-', label='R_D$_2$O=1mm, b=1, 1Scattering')
plt.xlabel('Q[Å$^-$$^1$]')
plt.ylabel('S[/incident particle/atom]')
plt.grid()
plt.legend(fontsize=12*1.5)
plt.tight_layout()
plt.show()
