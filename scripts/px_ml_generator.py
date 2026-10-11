# coding: utf-8
import matplotlib.pyplot as plt

# https://kdepy.readthedocs.io/en/latest/kernels.html, kernels can be plot as 
from KDEpy import NaiveKDE
for name, func in NaiveKDE._available_kernels.items():
   x, y = NaiveKDE(kernel=name).fit([0]).evaluate()
   plt.plot(x, y, label=name + (' (F)' if func.finite_support else ''))
plt.grid(True, ls='--', zorder=-15); plt.legend();
plt.show()
get_ipython().system('. ~/git/cinema/env.sh')
import os
import numpy as np
import kdsource as kds
import mcpl

inputfile = "bl6.mcpl"
cutoutput = "bl6_cut.mcpl"
cutoff_eV = 10

# !<cinema-build>/bin/mcpl_cut $inputfile $output $cutoff_eV

# !pymcpltool --stats --pdf $output
# !mv mcpl.pdf mcpl_cut_res.pdf


N=mcpl.MCPLFile(cutoutput).nparticles

# PList: wrapper for MCPL file
plist = kds.PList(cutoutput)
# # Geometry: define metrics for variables
# geom = kds.Geometry([kds.geom.Lethargy(cutoff_eV*1e-6),
#                      kds.geom.SurfXY(),
#                      kds.geom.Polar(),
#                      kds.geom.Decade()])
# var_importance = [5,1,1,3,3,3]

# Geometry: define metrics for variables
geom = kds.Geometry([kds.geom.Lethargy(cutoff_eV*1e-6),
                     kds.geom.SurfXY(),
                     kds.geom.Isotrop(),
                     kds.geom.Decade()])
var_importance = [5,1,1,3,3,3,3]

# Create KDSource
s = kds.KDSource(plist, geom,  kernel='epa')

# Give a little more importance to energy
print(geom.varnames)

parts,ws = s.plist.get(N=-1)
scaling = s.geom.std(parts=parts)
scaling /= var_importance
# Method 3: Adaptive Maximum Likelihood Cross-Validation:
# Creates a grid of adaptive bandwidths and evaluates the
# cross-validation scores on each one, which is an indicator of the
# quality of the estimation. Selects the bandwidth that optimizes
# CV score.
# kNN is used to generate the seed adaptive bandwidth.

# kNN bandwidth
s.bw_method = "knn"
batch_size = 10000 # Batch size for KNN search
k = 10             # Numer of neighbors per batch
s.fit(N, scaling=scaling, batch_size=batch_size, k=k)
bw_knn = s.kde.bw
bw_knn = s.kde.bw

# MLCV optimization of previously calculated kNN bandwidth
s.bw_method = "mlcv"
N_cv = int(1E4)   # Use a smaller N to reduce computation times
seed = bw_knn[:N_cv] # Use kNN BW as seed (first N elements)
grid = np.logspace(-1, -0.4,10)
s.fit(N_cv, scaling=scaling, seed=seed, grid=grid)
bw_cv = s.kde.bw
# Extend MLCV optimization to full KNN BW
bw_knn_cv = bw_knn * bw_cv[0]/bw_knn[0] # Apply MLCV factor
dim = s.geom.dim
bw_knn_cv *= kds.kde.bw_silv(dim,len(bw_knn))/kds.kde.bw_silv(dim,len(bw_cv)) # Apply Silverman factor

s = kds.KDSource(plist, geom, bw=bw_knn_cv,  kernel='epa') # Create new KDSource with full BW
s.fit(N=N, scaling=scaling)
s.plot_t
xmlfile = "source.xml"
s.save(xmlfile) # Save KDSource to XML file
resN=1000000
resampled = "resampled"
gzext = ".mcpl.gz"

# kdtool ships in the KDSource build prefix under $CINEMAPATH/external/KDSource
kdtool = os.path.join(os.environ.get('CINEMAPATH', '.'),
                      'external', 'KDSource', 'install', 'bin', 'kdtool')
get_ipython().system(f'time {kdtool} resample source.xml -o $resampled -n $resN')
get_ipython().system('pymcpltool --stats --pdf resampled.mcpl.gz')
get_ipython().system('mv mcpl.pdf mcpl_res.pdf')
# os.system('')
# KL divergence
def kl_divergence(p, q):
    return np.sum(np.where(p != 0, p * np.log(p / q), 0))

# Histogram of MCPL particle list
def mcpl_hist(mcplfile, var, bins, part0=None, part1=None, **kwargs):
    pl = mcpl.MCPLFile(mcplfile)
    hist = np.zeros(len(bins)-1)
    I = 0
    for pb in pl.particle_blocks:
        parts = np.stack((pb.ekin,pb.x,pb.y,pb.z,pb.ux,pb.uy,pb.uz,pb.time), axis=1)
        mask1 = np.ones(len(parts), dtype=bool)
        if part0 is not None:
            mask1 = np.logical_and.reduce(part0 <= parts, axis=1)
        mask2 = np.ones(len(parts), dtype=bool)
        if part1 is not None:
            mask2 = np.logical_and.reduce(parts <= part1, axis=1)
        mask = np.logical_and(mask1, mask2)
        data = parts[mask][:,var]
        hist += np.histogram(data, bins=bins, weights=pb.weight[mask], **kwargs)[0]
        I += np.sum(pb.weight)
    hist /= I
    hist /= (bins[1:]-bins[:-1])
    return hist
EE = np.logspace(-10,-5,100)

fig,scores = s.plot_E(EE, label="KDE")

widths = (EE[1:]-EE[:-1])

hist = mcpl_hist('resampled.mcpl.gz', 0, EE)
plt.bar(EE[:-1], hist, width=widths, align="edge", linewidth=.5, ec="k",
        fc="g", alpha=.7, label="Resampled")

hist = mcpl_hist('bl6_cut.mcpl', 0, EE)
plt.bar(EE[:-1], hist, width=widths, align="edge", linewidth=.5, ec="k",
        fc="r", alpha=.27, label="original")


plt.legend()
plt.tight_layout()
plt.show()
print(s.geom.varnames)
tt = np.linspace(0,2,300)
# fig,[scores,errs] = s.plot_integr("t", tt, yscale="linear")

hist = mcpl_hist('resampled.mcpl.gz', 7, tt)
plt.bar(tt[:-1], hist, width=np.diff(tt), align="edge", linewidth=.5, ec="k",
        fc="g", alpha=.5, label="Resampled")


hist = mcpl_hist(cutoutput, 7, tt)
plt.bar(tt[:-1], hist, width=np.diff(tt), align="edge", linewidth=.5, ec="k",
        fc="r", alpha=.2, label="original")
plt.legend()
# pb.ekin, pb.x, pb.y, pb.z, pb.ux, pb.uy,pb.uz, pb.time
xx = np.linspace(20,45,20)
yy = np.linspace(0,25,20)
fig,scores = s.plot2D_integr(["x","y"], [xx,yy], scale="log")

plt.clim(vmin=1e-5)
plt.tight_layout()
plt.show()
xx = np.linspace(20,45,20)
yy = np.linspace(0,25,20)
fig,scores = s.plot2D_integr(["x","y"], [xx,yy], scale="lin")

plt.clim(vmin=1e-5)
plt.tight_layout()
plt.show()
