import numpy as np
from yn_ana_recordmcpl_code import SQTrueHist, MultiScatAnalysor, atomNum, SQHist
from Cinema.Experiment.Analyser.DataLoader import ErrorPropagator
from Cinema.Interface import plotStyle
import matplotlib.pyplot as plt
import os

# Base directory holding the simulated-output folders (the 'gd3'/'gd4'
# folders live directly inside it): point CINEMA_MPI2022_SIMDATA at it; when
# unset, the folders are resolved relative to the working directory, with a
# warning.
data_base = os.environ.get('CINEMA_MPI2022_SIMDATA')
if not data_base:
    print('Warning: CINEMA_MPI2022_SIMDATA is not set - falling back to the '
          "relative defaults 'gd3' and 'gd4'")
    data_base = '.'

# example for analyzing data in ScorerDeltaMomentum_SofQ_He_seed.record.mcpl.gz to get sqtrue of D2O in 1Dhist
numNeutron = 1.5e+7
d2o_atomNum, v_atomNum = atomNum(d2o_r=4.4758, d2o_h=14.3376, v_r=3.175, v_h=60.0)
d2o = SQTrueHist(os.path.join(data_base, 'gd3/*ScorerDeltaMomentum_SofQ_He_seed*.record.mcpl.gz'))
d2o_qtrue, d2o_s, d2o_err = d2o.fillHist(xmin=0.1, xmax=120.0, numbin=1000, linear=True)

v = SQTrueHist(os.path.join(data_base, 'gd4/*ScorerDeltaMomentum_SofQ_He_seed*.record.mcpl.gz'))
v_qtrue, v_s, v_err = v.fillHist(xmin=0.1, xmax=120.0, numbin=1000, linear=True)

# d2o_calibration and error_propagate
d2o_calib = ErrorPropagator(d2o_s/d2o_atomNum/numNeutron,  d2o_qtrue, error=d2o_err/d2o_atomNum/numNeutron)
d2o_calib.divide(v_s/v_atomNum/numNeutron,  v_err/v_atomNum/numNeutron, v_qtrue)
d2o_s_calib = d2o_calib.weight
d2o_s_calib_err = d2o_calib.error*d2o_calib.weight


# example for decomposing sqtrue of D2O in 1Dhist
d2oMS = MultiScatAnalysor(os.path.join(data_base, 'gd3/*ScorerDeltaMomentum_SofQ_He_seed*.record.mcpl.gz'))
d2oMS1_qtrue, d2oMS1_s, d2oMS1_err = d2oMS.sqHist(xmin=0.1, xmax=120.0, numbin=1000, scatnum=1, inelastic=True, linear=True)
d2oMS1_calib = ErrorPropagator(d2oMS1_s/d2o_atomNum/numNeutron,  d2oMS1_qtrue, error=d2oMS1_err/d2o_atomNum/numNeutron)
d2oMS1_calib.divide(v_s/v_atomNum/numNeutron,  v_err/v_atomNum/numNeutron, v_qtrue)
d2oMS1_s_calib = d2oMS1_calib.weight
d2oMS1_s_calib_err = d2oMS1_calib.error*d2oMS1_calib.weight

# plot
plotStyle()
plt.xlim(0.0, 16.0)
plt.ylim(-1.0, 6.0)
plt.errorbar(d2o_qtrue, d2o_s_calib , yerr=d2o_s_calib_err, fmt='o-', label='R_D$_2$O=4.4758mm, b=1, Total')
plt.errorbar(d2oMS1_qtrue, d2oMS1_s_calib , yerr=d2oMS1_s_calib_err, fmt='o-', label='R_D$_2$O=4.4758mm, b=1, 1Scattering')
plt.xlabel('Q[Å$^-$$^1$]')
plt.ylabel('S[/incident particle/atom]')
plt.grid()
plt.legend(fontsize=12*1.5)
plt.tight_layout()
plt.show()
