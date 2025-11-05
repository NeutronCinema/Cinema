#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import optuna
from sklearn.neighbors import KernelDensity
import time
from Cinema.Prompt.histogram import Hist2D, Hist1D
import mcpl
from Cinema.Interface import plotStyle

plotStyle()


def unitVectoSph(dir):
    x, y, z = dir
    theta = np.arctan(y/x)
    phi = np.arccos(z)
    return np.array([theta, phi])


class Source:
    def __init__(self, data) -> None:
        pass


class ParticleSet:
    def __init__(self, data) -> None:
        self.data_raw=np.array(data, dtype=np.float64)

    # make data in [-1, 1]
    def transform(self, p = None): 
        if p is None:
            return ((self.data.T/self.L) -self.offset).T
        else: 
            return ((p.T/self.L) -self.offset).T
    
    def inv(self, p = None):
        if p is None:
            (self.data+self.offset)*self.L
        else:
            return (p+self.offset)*self.L
        
    def getDist(self, lower=1e-3, upper=1e9, bin=30, w=None, log=False, raw=True):
        hist = Hist1D(lower, upper, bin, log) 
        if raw:
            hist.fillmany(self.data_raw, w)
        else:
            hist.fillmany(self.data, w)
        x = hist.getCentre()
        y = hist.getWeight()/np.diff(hist.getEdges())
        return x, y/np.trapz(y,x)
    


class ParticleSetLin(ParticleSet):
    def __init__(self, data) -> None:
        super().__init__(data)  
        self.data = data
        self.min = self.data.min(axis=-1)
        self.max = self.data.max(axis=-1)
        self.L = (self.max-self.min)/2
        self.offset = self.min/self.L+1   
        self.L=1
        self.offset=0 
        self.data = self.transform(self.data) 

class ParticleSetLog(ParticleSet):
    def __init__(self, data) -> None:
        super().__init__(data)
        if any(data<0.):
            raise RuntimeError('negtive data with the log mode')
        self.data=np.log(data)

    def transform(self, p = None): 
        if p is None:
            return self.data
        else: 
            return p
    
    def inv(self, p = None):
        if p is None:
            return self.data_raw
        else: 
            return np.exp(p)
  

class SourceTrainer:
    def __init__(self, fn) -> None:
        myfile = mcpl.MCPLFile(fn)
        self.n = myfile.nparticles
        myfile = mcpl.MCPLFile(fn, blocklength=self.n)

        block = myfile._currentblock
        for block in myfile.particle_blocks:
            self.pos = ParticleSetLin(block.position)

            x, y, z = block.direction.T
            self.theta = ParticleSetLin(np.arctan(y/x))
            self.phi = ParticleSetLin(np.arccos(z))

            self.t = ParticleSetLog(block.time) #in ms
            self.en = ParticleSetLog(block.ekin*1e6)   # MeV->eV

            self.w = block.weight
            break

    
    def getMeanWeight(self):
        return self.w.sum()/self.n
    
    # def makeInput(self, targetW=1.): # fixme: missing split
    #     mcw = np.random.random(self.n)
    #     coeff = mcw*targetW
    #     idx = coeff < self.w
    #     x,y,z = self.pos.transform()[idx].T
    #     # return np.stack((self.en.transform()[idx], x,y,z, self.theta.transform()[idx], self.phi.transform()[idx], self.t.transform()[idx] ),axis = -1)
    #     # return np.stack((self.en.data[idx], self.t.transform()[idx] ),axis = -1)
    #     return np.stack((self.en.data[idx], self.t.data[idx] ), axis = -1)

    
    def train(self, dumpFileName=None):
        
        x,y,z = self.pos.data.T
        # ds = np.stack((self.en.data, x,y,z, self.theta.data, self.phi.data, self.t.data ),axis = -1)

        ds = np.stack((self.en.data, self.t.data, self.theta.data, self.phi.data, x, y, z),axis = -1)
        print(f'ds.shape {ds.shape}')

        from sklearn.preprocessing import PowerTransformer, QuantileTransformer, MinMaxScaler
        self.pt = QuantileTransformer(output_distribution='normal', n_quantiles=1000)
        self.pt.fit(ds)
        ds = self.pt.transform(ds)

        clf = KernelDensity(leaf_size=4000, bandwidth='silverman') # 'scott', 'silverman'
        clf.fit(ds)
        return clf

        # clf = KernelDensity(leaf_size=4000, algorithm = 'ball_tree')
        # param_distributions = {
        #     'bandwidth': optuna.distributions.FloatDistribution(1e-4, 1, log=False)
        # }
        # optuna_search = optuna.integration.OptunaSearchCV(clf, param_distributions, n_trials=10, verbose=3)
        # optuna_search.fit(ds[:10000], sample_weight=self.w[:10000])

        # kd = optuna_search.best_estimator_
        # if dumpFileName is not None:
        #     import pickle
        #     f = open (dumpFileName, 'wb')
        #     pickle.dump(kd, f)
        #     f.close()
        # return kd

s = SourceTrainer('bl6.mcpl.gz')
t1 = time.time()
model = s.train(dumpFileName='kd.pickle')

print(f'train {time.time()-t1}s')


attr = ['en', 't', 'theta', 'phi']
idx = [0, 1, 2, 3]
plotlog=[True, True, False, False]
hist={}

for d in attr:
    hist[d] = Hist1D(1e-3, 1e9, 30, False) 

for loop in range(10):
    t1 = time.time()
    sample = model.sample(10_000_000, random_state=loop)
    print(f'sample {time.time()-t1} s')

    t1 = time.time()
    res = s.pt.inverse_transform(sample)
    print(f'inverse_transform time {time.time()-t1}')

    t1 = time.time()
    for d, i in zip(attr, idx):
        obj = getattr(s, d)
        hist_kd = hist[d]  
        hist_kd.fillmany(obj.inv(res[:, i]))
    print(f'filling time {time.time()-t1}')




from matplotlib.backends.backend_pdf import PdfPages


pp = PdfPages('summary.pdf')

for d, log in zip(attr, plotlog):
    plt.figure()
    obj = getattr(s, d)
    en, den = obj.getDist(w=s.w)
    if log:
        plt.loglog(en, den, label='raw')
    else:
        plt.semilogy(en, den, label='raw')

    hist_kd = hist[d]
    x = hist_kd.getCentre()
    y = hist_kd.getWeight()/np.diff(hist_kd.getEdges())

    if log:
        plt.loglog(x, y/np.trapz(y,x), label='sampled')
    else:
        plt.semilogy(en, den, label='raw')
    plt.legend(loc=0)
    plt.title(d+' density')
    pp.savefig()
    plt.close()


    ## Hist
    plt.figure()
    if log:
        plt.semilogx(en, den*en, label='raw')
    else:
        plt.plot(en, den*en, label='raw')

    hist_kd = hist[d]
    x = hist_kd.getCentre()
    y = hist_kd.getWeight()/np.diff(hist_kd.getEdges())

    if log:
        plt.semilogx(x, y/np.trapz(y,x)*x, label='sampled')
    else:
        plt.plot(x, y/np.trapz(y,x)*x, label='sampled')
    plt.legend(loc=0)
    plt.title(d+f' hist {hist_kd.getWeight().sum()}')
    pp.savefig()
    plt.close()


pp.close()









        


        


    





# blocksize = 10000
# myfile = mcpl.MCPLFile('bl6_1keV.mcpl', blocksize)

# nparticles = myfile.nparticles

# hist_raw = Hist1D(1e-5, 1000, 100, False) 


# data=np.zeros([blocksize, 8])
# print(f'nparticles: {nparticles}, blocksize: {blocksize}')

# for p in myfile.particle_blocks:
#     data[:, :3] = p.position*10 # cm->mm
#     data[:, 3:6] = p.direction
#     data[:, 6] = np.log(p.ekin*1e6)     # MeV->eV
#     data[:, 7] = p.weight
#     break

# hist_raw.fillmany(np.exp(data[:, 6] ), data[:, 7] )
# hist_raw.plot(log=True)


# clf = KernelDensity()
# param_distributions = {
#     'bandwidth': optuna.distributions.FloatDistribution(1e-2, 1e2, log=True)
# }
# optuna_search = optuna.integration.OptunaSearchCV(clf, param_distributions, n_trials=10)
# optuna_search.fit(data[:, 6][:, np.newaxis], sample_weight=data[:, 7])

# kd =  optuna_search.best_estimator_

# hist_kd = Hist1D(1e-5, 1000, 100, False) 

# t1 = time.time()
# sample = kd.sample(100000)
# hist_kd.fillmany(np.exp(sample[:, 0]) )
# print(f'time diff {time.time()-t1}')
# hist_kd.plot(show=True, log=True)
