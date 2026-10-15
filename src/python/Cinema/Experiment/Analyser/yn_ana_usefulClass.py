#!/usr/bin/env python3
import numpy as np
from glob import glob
import os
import re
from Cinema.Interface.units import *
from Cinema.Interface.helper import *
from Cinema.Experiment.Analyser import ErrorPropagator, IDFLoader, DataLoader, RunData, Normalise
from Cinema.Prompt.histogram import *
from Cinema.Prompt import PromptFileReader

def atomNumLW_Stick(h2o_r, h2o_h): # mm
    h2o_density = 0.100104/np.power(1/mm, 3) # atoms/mm^3 
    h2o_volume=np.pi*np.square(h2o_r)*h2o_h
    h2o_atomNum=h2o_volume*h2o_density
    return h2o_atomNum

def atomNum_Stick(d2o_r, d2o_h, v_r, v_h): # mm
    d2o_density = 0.0997033/np.power(1/mm, 3) # atoms/mm^3
    v_density = 0.0723244/np.power(1/mm, 3) # atoms/mm^3
    
    d2o_volume=np.pi*np.square(d2o_r)*d2o_h
    v_volume=np.pi*np.square(v_r)*v_h
    d2o_atomNum=d2o_volume*d2o_density
    v_atomNum=v_volume*v_density
    return d2o_atomNum, v_atomNum

def atomNum_Sphere(d2o_r,  v_r): # mm
    d2o_density = 0.0997033/np.power(1/mm, 3) # atoms/mm^3
    v_density = 0.0723244/np.power(1/mm, 3) # atoms/mm^3
    
    d2o_volume=4/3*np.pi*np.power(d2o_r, 3)
    v_volume=4/3*np.pi*np.power(v_r, 3)
    d2o_atomNum=d2o_volume*d2o_density
    v_atomNum=v_volume*v_density
    return d2o_atomNum, v_atomNum

def reduction(rundata, moduleName):
    # Directory with the MPI2022 IDF pixel-layout files: point
    # CINEMA_MPI2022_DATA at a site-specific absolute location; the default is
    # the relative path 'mpi_experiment_2022/idf' (resolved against the
    # working directory).
    idf_dir = os.environ.get('CINEMA_MPI2022_DATA')
    if not idf_dir:
        print('Warning: CINEMA_MPI2022_DATA is not set - falling back to the '
              "relative default 'mpi_experiment_2022/idf'")
        idf_dir = 'mpi_experiment_2022/idf'
    idf = IDFLoader(idf_dir)
    tree = idf.query(moduleName)

    mod2sample = 30000. # length unit: mm
    sam2det = np.linalg.norm(tree.location, axis=1) # length unit: mm
    mod2det = mod2sample + sam2det  # length unit: mm
    qehist = Est1D(0.1, 50.1, 1000, True)
        
    for plxIdx in range(rundata.detErrPro.weight.shape[0]):
        # print(f'pixel ID {plxIdx} {rundata.detErrPro.weight.shape[0]}')
        speedAtPixel = mod2det[plxIdx]/rundata.tofCentre # velocity unit: mm/s
        ekin = neutron_mass_evc2*np.square(speedAtPixel*mm)/2 # energy unit: eV
        pixelLocation = tree.location[plxIdx]
        # cosAngle = pixelLocation.dot(np.array([0.,0.,1.]))/sam2det[plxIdx]
        cosAngle = pixelLocation[2]/sam2det[plxIdx]
        # print(f'mean scattering angle {np.arccos(cosAngle.mean())/(np.pi/180.)}')
        q = angleCosine2Q(cosAngle, ekin, ekin)
        qehist.fillmany(q, rundata.detErrPro.weight[plxIdx, :], rundata.detErrPro.error[plxIdx, :])
    return qehist


class McplAnalysor1D(PromptFileReader):
    def __init__(self,filePath):
        self.filePath = filePath
        
    def filesMany(self):
        path = os.path.join(self.filePath)
        files = glob(path)
        files.sort(key=lambda l: int(re.findall('\d+', l)[-1]))
        return files

    def getHist(self):
        super().__init__(self.filePath)
        edge = self.getData('edge')
        content = self.getData('content')
        hit = self.getData('hit')
        hist = ErrorPropagator(weight=content,  xcentre=edge, count=hit, error = None)
        return hist
    
    def getHistMany(self, seedStart, seedEnd):
        files = self.filesMany()
        self.filePath = files[seedStart-1]
        histMany = self.getHist()
        for i in range(seedStart, seedEnd):
            self.filePath = files[i]
            print(self.filePath)
            histMany += self.getHist()
        return histMany

class ExpTOF(RunData):
    def __init__(self, filePath):
        self.filePath = filePath
        
    def getModuTOF(self, moduleName, tofcut=1, normMethod=Normalise.byMonitor):
        super().__init__(self.filePath, moduleName, tofcut, normMethod)
        tof_module = self.detErrPro.ycentre
        weightPidSum_module = np.sum(self.detErrPro.weight, axis=0) 
        errSquare_module = np.sum(np.square(self.detErrPro.error), axis=0)
        err_module = np.sqrt(errSquare_module)
        moduleTOF = ErrorPropagator(weight=weightPidSum_module, xcentre=tof_module, error=err_module)
        return moduleTOF
    
    def getModuTOFMany(self, moduleList, tofcut=1, normMethod=Normalise.byMonitor):
        modulesTOF = self.getModuTOF(moduleList[0], tofcut, normMethod)
        for moduleName in moduleList[1:]:
            modulesTOF += self.getModuTOF(moduleName, tofcut, normMethod)
        return modulesTOF


    
class RebinHist1D():
    def __init__(self, edge, content, error=None):
        self.edge = edge
        self.content = content
        self.error = error
        self.unitcontent = self.content/np.diff(self.edge)
        if self.error is not None:
            self.uniterror = self.error/np.diff(self.edge)
    
    def mergeBin(self, binNum):
        binNum = int(binNum)
        if self.content.shape[0]%binNum == 0:
            unitNum = int(self.content.shape[0]/binNum)
            edge_new = np.zeros(binNum+1)
            content_new = np.zeros(binNum)
            edge_new[0] = self.edge[0]
            for i in range(0, binNum):
                 edge_new[i+1] = self.edge[unitNum*(i+1)]
                 content_new[i] = np.sum(self.content[unitNum*i:unitNum*(i+1)])
            
            if self.error is not None:
                error_new = np.zeros(binNum)
                for i in range(0, binNum):
                    error_new[i] = np.sqrt(np.sum(np.square(self.error[unitNum*i:unitNum*(i+1)])))
                self.error = error_new
                self.uniterror = error_new/np.diff(edge_new) 
            self.edge = edge_new
            self.content = content_new
            self.unitcontent = content_new/np.diff(edge_new)       
        else:
            print('Input hist can not be rebined')
    
    def linearBin2log(self, binNum): # optimize this function???
        binNum = int(binNum)
        if self.edge[0] >= 0:
            if self.edge[0] == 0:
                self.edge[0] = 1e-6
            edge_new = np.logspace(np.log10(self.edge[0]), np.log10(self.edge[-1]), binNum+1)
            edge_new[0] = self.edge[0] 
            edge_new[-1] = self.edge[-1] # floating-point number problem???
            content_new = np.zeros(binNum) 
            for i in range(0, binNum):
                idxStart = np.where(self.edge<=edge_new[i])[0][-1]+1
                idxEnd = np.where(self.edge>=edge_new[i+1])[0][0]-1
                if idxStart>idxEnd:
                    content_new[i] = self.unitcontent[idxStart-1]*(edge_new[i+1]-edge_new[i])
                    
                elif idxStart==idxEnd:
                    content_new[i] = self.unitcontent[idxStart-1]*(self.edge[idxStart]-edge_new[i]) + self.unitcontent[idxEnd]*(edge_new[i+1]-self.edge[idxEnd])
                else:
                    middle = self.unitcontent[idxStart:idxEnd]*np.diff(self.edge[idxStart:idxEnd+1])
                    content_new[i] = self.unitcontent[idxStart-1]*(self.edge[idxStart]-edge_new[i]) + self.unitcontent[idxEnd]*(edge_new[i+1]-self.edge[idxEnd]) + np.sum(middle)

            if self.error is not None: 
                error_new = np.zeros(binNum)
                errorSquare_new = np.zeros(binNum) 
                for i in range(0, binNum):
                    idxStart = np.where(self.edge<=edge_new[i])[0][-1]+1
                    idxEnd = np.where(self.edge>=edge_new[i+1])[0][0]-1
                    if idxStart>idxEnd:
                        errorSquare_new[i] = np.square(self.uniterror[idxStart-1]*(edge_new[i+1]-edge_new[i]))
                    
                    elif idxStart==idxEnd:
                        errorSquare_new[i] = np.square(self.uniterror[idxStart-1]*(self.edge[idxStart]-edge_new[i])) + np.square(self.uniterror[idxEnd]*(edge_new[i+1]-self.edge[idxEnd]))
                    else:
                        midddle = np.square(self.uniterror[idxStart:idxEnd]*np.diff(self.edge[idxStart:idxEnd+1]))
                        errorSquare_new[i] = np.square(self.uniterror[idxStart-1]*(self.edge[idxStart]-edge_new[i])) + np.square(self.uniterror[idxEnd]*(edge_new[i+1]-self.edge[idxEnd]))+np.sum(midddle)
                error_new = np.sqrt(errorSquare_new)
                self.error = error_new
                self.uniterror = error_new/np.diff(edge_new) 
            self.edge = edge_new
            self.content = content_new
            self.unitcontent = content_new/np.diff(edge_new)
            
        else:
            print('xmin of linear hist is negative')
            
            
        
        
            
# edge = np.array([0.0, 2000, 4000, 6000, 8000, 10000])
# # edge = np.array([0.0, 0.002, 0.004, 0.006, 0.008, 0.01])
# content = np.array([20000, 30000, 60000, 50000, 80000])
# error = np.array([200, 300, 400, 100, 400])

# hist = RebinHist1D(edge, content, error)
# print(hist.edge)
# hist.linearBin2log(2)
# print(hist.edge)
# print(hist.content)
# print(hist.error)
# print(hist.unitcontent)
