import numpy as np
from Cinema.Prompt import PromptFileReader
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from glob import glob
import os
import re

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
        return edge, content
    
    def getHistMany(self, seedStart, seedEnd):
        files = self.filesMany()
        content_sum = 0
        for i in range(seedStart-1, seedEnd):
            self.filePath = files[i]
            edge, content = self.getHist()
            content_sum += content
        return edge, content_sum
    
    def plotHist(self, edge, content):
        plt.plot(edge[:-1], content/np.diff(edge), label=f'total weight={content.sum()}')
        plt.grid()
        plt.legend()
        plt.show()
        
class McplAnalysor2D(PromptFileReader):
    def __init__(self,filePath):
        self.filePath = filePath
        
    def filesMany(self):
        path = os.path.join(self.filePath)
        files = glob(path)
        files.sort(key=lambda l: int(re.findall('\d+', l)[-1]))
        return files

    def getHist(self):
        super().__init__(self.filePath)
        xedge = self.getData('xedge')
        yedge = self.getData('yedge')
        content = self.getData('content')
        hit = self.getData('hit')
        return xedge, yedge, content, hit
    
    def getHistMany(self, seedStart, seedEnd):
        files = self.filesMany()
        content_sum = 0
        hit_sum = 0
        for i in range(seedStart-1, seedEnd):
            self.filePath = files[i]
            xedge, yedge, content, hit = self.getHist()
            content_sum += content
            hit_sum += hit
        return xedge, yedge, content_sum, hit_sum
    
    def plotHist(self, xedge, yedge, content, hit, logscale=False):
        X, Y = np.meshgrid(xedge, yedge)
        fig=plt.figure()
        ax = fig.add_subplot(111)
        if logscale:
            pcm = ax.pcolormesh(X, Y, content.T, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=content.max()*1e-10, vmax=content.max()), shading='auto')
        else:
            pcm = ax.pcolormesh(X, Y, content.T, cmap=plt.cm.jet,shading='auto')
        fig.colorbar(pcm, ax=ax)
        hit = hit.sum()
        integral= content.sum()
        plt.title(f'ScorerPSD_NeutronHistMap, integral {integral}, count {hit}')
        plt.figure()
        plt.subplot(211)
        plt.plot(xedge[:-1]+np.diff(xedge)*0.5, content.sum(axis=1))
        plt.xlabel('integral x')
        plt.title('ScorerPSD_NeutronHistMap')
        plt.subplot(212)
        plt.plot(yedge[:-1]+np.diff(yedge)*0.5, content.sum(axis=0))
        plt.xlabel('integral y')
        plt.show()
  
    
# McplAnalysor2D example
# psd = McplAnalysor2D('<sim-data-dir>/gdml/scorer/ScorerPSD_NeutronHistMap_seed4096.mcpl.gz')
# x_hist, y_hist, content_hist, hit_hist = psd.getHist()
# print(x_hist.shape)
# print(y_hist.shape)
# print(content_hist.shape)
# psd.plotHist(x_hist, y_hist, content_hist, hit_hist)

# Base directory holding the simulated-output folders (the 'gd3' folder lives
# directly inside it): point CINEMA_MPI2022_SIMDATA at it; when unset, the
# folder is resolved relative to the working directory, with a warning.
data_base = os.environ.get('CINEMA_MPI2022_SIMDATA')
if not data_base:
    print('Warning: CINEMA_MPI2022_SIMDATA is not set - falling back to the '
          "relative default 'gd3'")
    data_base = 'gd3'
psd = McplAnalysor2D(os.path.join(data_base, '*ScorerPSD_NeutronHistMapM300_seed*.mcpl.gz'))
x_hist, y_hist, content_hist, hit_hist = psd.getHistMany(seedStart=1, seedEnd=15) 
print(x_hist.shape)
print(y_hist.shape)
print(content_hist.shape)   
psd.plotHist(x_hist, y_hist, content_hist, hit_hist)  


