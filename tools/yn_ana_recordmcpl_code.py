import numpy as np
from Cinema.Prompt import PromptFileReader
from Cinema.Prompt.histogram import Hist1D
from Cinema.Interface.units import avogadro
from glob import glob
import os
import re

# atom number in material
def atomNum(d2o_r, d2o_h, v_r, v_h): # mm
    d2o_density = 1.10526/1000 # g/mm3
    d2o_molmass = 2*2+16 # g/mol
    d2o_num = 3
    v_density = 6.11/1000 # g/mm3
    v_molmass = 50.94 # g/mol
    v_num = 1
    d2o_volume=np.pi*np.square(d2o_r)*d2o_h
    v_volume=np.pi*np.square(v_r)*v_h
    d2o_atomNum=d2o_volume*d2o_density/d2o_molmass*avogadro*d2o_num
    v_atomNum=v_volume*v_density/v_molmass*avogadro*v_num
    return d2o_atomNum, v_atomNum

class RecordMcplAnalysor(Hist1D):
    def __init__(self, filePath, xname, weightname):
        path=os.path.join(filePath)
        self.files = glob(path)
        self.files.sort(key=lambda l: int(re.findall('\d+', l)[-1]))
        self.xname = xname
        self.weightname = weightname

    def densityHist(self):
        x_hist = self.getCentre()
        y_hist = self.getWeight()/np.diff(self.getEdges())
        return x_hist, y_hist

    def fillHist(self, xmin, xmax, numbin, linear=True, scatnum=None):
        super().__init__(xmin, xmax, numbin, linear)
        for fname in self.files:
            f = PromptFileReader(fname)
            for p in f.blockIterator():
                x = f.getRecordData(p, self.xname)
                weight = f.getRecordData(p, self.weightname)
                if scatnum != None:
                    numScat = f.getRecordData(p, 'scatNum')
                    idx = np.where(numScat==scatnum)
                    x = x[idx]
                    weight = weight[idx]
                self.fillmany(x, weight)
        x_hist, y_hist = self.densityHist()
        uncet = np.sqrt(self.getHit()/10.)
        err_hist = np.divide(y_hist, uncet, where=(uncet!=0.))
        return x_hist, y_hist, err_hist

class SQTrueHist(RecordMcplAnalysor):
    def __init__(self, filePath):
        super().__init__(filePath, 'qtrue', 'weight')

class SQHist(RecordMcplAnalysor):
    def __init__(self, filePath):
        super().__init__(filePath, 'q', 'weight')

class MultiScatAnalysor(RecordMcplAnalysor):
    def __init__(self, filePath):
        self.filePath = filePath

    def sqHist(self, xmin, xmax, numbin, scatnum, inelastic=True, linear=True):
        if inelastic:
            super().__init__(self.filePath, 'qtrue', 'weight')
        else:
            super().__init__(self.filePath, 'q', 'weight')
        q_hist, s_hist, err_hist= self.fillHist(xmin, xmax, numbin, linear, scatnum)
        return q_hist, s_hist, err_hist

    def probaMultiScat(self, scatnum):
        super().__init__(self.filePath, 'scatNum', 'weight')
        proba = 0
        for fname in self.files:
            f = PromptFileReader(fname)
            for p in f.blockIterator():
                scatNum = f.getRecordData(p, self.xname)
                idx = np.where(scatNum==scatnum)
                weight = f.getRecordData(p, self.weightname)[idx]
                proba += np.sum(weight)
        return proba
        
