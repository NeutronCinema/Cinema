////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  you may not use this file except in compliance with the License.          //
//  You may obtain a copy of the License at                                   //
//                                                                            //
//      http://www.apache.org/licenses/LICENSE-2.0                            //
//                                                                            //
//  Unless required by applicable law or agreed to in writing, software       //
//  distributed under the License is distributed on an "AS IS" BASIS,         //
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  //
//  See the License for the specific language governing permissions and       //
//  limitations under the License.                                            //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

#include "PTPython.hh"
#include "PTHistBase.hh"
#include "PTHist1D.hh"
#include "PTHist2D.hh"
#include "PTEst1D.hh"


namespace pt = Prompt;


unsigned pt_HistBase_dimension(void* obj)
{
  return static_cast<pt::HistBase *>(obj)->dimension();
}

void pt_HistBase_merge(void* obj, void* obj2)
{
  auto hist1 = static_cast<pt::HistBase*>(obj);
  hist1->merge(*static_cast<pt::HistBase*>(obj2));
}

void pt_HistBase_setWeight(void *obj, double *data, size_t n)
{
  auto hist = static_cast<pt::HistBase*>(obj);
  hist->setWeight(data, n);
}

void pt_HistBase_setHit(void *obj, double *data, size_t n)
{
  auto hist = static_cast<pt::HistBase*>(obj);
  hist->setHit(data, n);
}

void pt_HistBase_setWW(void *obj, double *data, size_t n)
{
  auto hist = static_cast<pt::HistBase*>(obj);
  hist->setWW(data, n);
}


double pt_HistBase_getXMin(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getXMin();
}

double pt_HistBase_getXMax(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getXMax();
}

double pt_HistBase_getTotalWeight(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getTotalWeight();
}

double pt_HistBase_getAccWeight(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getAccWeight();
}

double pt_HistBase_getOverflow(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getOverflow();
}

double pt_HistBase_getUnderflow(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getUnderflow();
}

double pt_HistBase_getTotalHit(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getTotalHit();
}

size_t pt_HistBase_getDataSize(void* obj)
{
  return static_cast<pt::HistBase*>(obj)->getDataSize();
}
void pt_HistBase_scale(void* obj, double scale)
{
  static_cast<pt::HistBase*>(obj)->scale(scale);
}

void pt_HistBase_reset(void* obj)
{
  static_cast<pt::HistBase*>(obj)->reset();
}

void pt_HistBase_getRaw(void* obj, double *data)
{
  auto cdata = static_cast<pt::Hist1D *>(obj)->getRaw();
  for(size_t i=0;i<cdata.size();i++)
  {
    data[i] = cdata[i];
  }
}

void pt_HistBase_getww(void *obj, double *data)
{
  auto cdata = static_cast<pt::Hist1D *>(obj)->getww();
  for(size_t i=0;i<cdata.size();i++)
  {
    data[i] = cdata[i];
  }
}

void pt_HistBase_getww_2dalias(void *obj, double *data)
{
  pt_HistBase_getww(obj, data);
}


void pt_HistBase_getHit(void* obj, double* data)
{
  auto cdata = static_cast<pt::Hist1D *>(obj)->getHit();
  for(size_t i=0;i<cdata.size();i++)
  {
    data[i] = cdata[i];
  }
}

const char* pt_HistBase_getName(void* obj)
{
  return static_cast<pt::Hist1D *>(obj)->getName().c_str();
}


void* pt_Hist1D_new(double xmin, double xmax, unsigned nbins, bool linear)
{
    return static_cast<void *>(new pt::Hist1D("pt_Hist1D_new", xmin, xmax, nbins, linear));
}

void pt_Hist1D_getEdge(void* obj, double* edge)
{
  auto edgevec = static_cast<pt::Hist1D *>(obj)->getEdges();
  for(size_t i=0;i<edgevec.size();i++)
  {
    edge[i]=edgevec[i];
  }
}

void pt_Hist1D_getWeight(void* obj, double* w)
{
  auto weight = static_cast<pt::Hist1D *>(obj)->getRaw();
  // w = weight.data();
  for(size_t i=0;i<weight.size();i++)
  {
    w[i] = weight[i];
  }
}

void pt_Hist1D_getHit(void* obj, double* h)
{
  auto hit = static_cast<pt::Hist1D *>(obj)->getHit();
  for(size_t i=0;i<hit.size();i++)
  {
    h[i] = hit[i];
  }
}


unsigned pt_Hist1D_getNumBin(void* obj)
{
  return static_cast<pt::Hist1D *>(obj)->getDataSize();
}


void pt_Hist1D_fill(void* obj, double val, double weight)
{
  static_cast<pt::Hist1D *>(obj)->fill(val, weight);
}

void pt_Hist1D_fillmany(void* obj, size_t n, double* val, double* weight)
{
  for(size_t i=0;i<n;i++)
    static_cast<pt::Hist1D *>(obj)->fill(val[i], weight[i]);
}

void pt_Hist1D_delete(void* obj)
{
  delete static_cast<pt::Hist1D *>(obj);
}


// pt::Hist2D
void* pt_Hist2D_new(double xmin, double xmax, unsigned nxbins,
                    double ymin, double ymax, unsigned nybins)
{
  return static_cast<void *>(new pt::Hist2D("pt_Hist2D_new", xmin, xmax, nxbins,
                                            ymin, ymax, nybins));
}

void pt_Hist2D_delete(void* obj)
{
  delete static_cast<pt::Hist2D *>(obj);
}

void pt_Hist2D_getWeight(void* obj, double* w)
{
  auto weight = static_cast<pt::Hist2D *>(obj)->getRaw();
  for(size_t i=0;i<weight.size();i++)
  {
    w[i] = weight[i];
  }
}

void pt_Hist2D_merge(void* obj, void* obj2)
{
  auto hist1 = static_cast<pt::Hist2D*>(obj);
  hist1->merge(*static_cast<pt::HistBase*>(obj2));
}

double pt_Hist2D_getYMin(void* obj)
{
  return static_cast<pt::Hist2D*>(obj)->getYMin();
}

double pt_Hist2D_getYMax(void* obj)
{
  return static_cast<pt::Hist2D*>(obj)->getYMax();
}

unsigned  pt_Hist2D_getNBinX(void* obj)
{
  return static_cast<pt::Hist2D*>(obj)->getNBinX();
}

unsigned  pt_Hist2D_getNBinY(void* obj)
{
  return static_cast<pt::Hist2D*>(obj)->getNBinY();
}

void pt_Hist2D_fill(void* obj, double xval, double yval, double weight)
{
  static_cast<pt::Hist2D *>(obj)->fill(xval, yval, weight);
}

void pt_Hist2D_fillmany(void* obj, size_t n, double* xval, double* yval, double* weight)
{
  for(size_t i=0;i<n;i++)
    static_cast<pt::Hist2D *>(obj)->fill(xval[i], yval[i], weight[i]);
}

void pt_Hist2D_getHit(void* obj, double* h)
{
  auto hit = static_cast<pt::Hist2D *>(obj)->getHit();
  for(size_t i=0;i<hit.size();i++)
  {
    h[i] = hit[i];
  }
}


void pt_Hist2D_getDensity(void* obj, double* d)
{
  auto nbin = static_cast<pt::Hist2D *>(obj)->getDataSize();
  auto weight = static_cast<pt::Hist2D *>(obj)->getRaw();
  auto hit = static_cast<pt::Hist2D *>(obj)->getHit();
  for(size_t i=0;i<nbin;i++)
  {
    if(hit[i])
      d[i]=weight[i]/hit[i];
  }
}

// pt::Hist1D
void* pt_Est1D_new(double xmin, double xmax, unsigned nbins, bool linear)
{
  return static_cast<void *>(new pt::Est1D("pt_Est1D_new", xmin, xmax, nbins, linear));
}

void pt_Est1D_delete(void* obj)
{
  delete static_cast<pt::Est1D *>(obj);
}

void pt_Est1D_fill(void* obj, double val, double weight, double error)
{
  static_cast<pt::Est1D *>(obj)->fill(val, weight, error);
}

void pt_Est1D_fillmany(void* obj, size_t n, double* val, double* weight, double* error)
{
  auto o = static_cast<pt::Est1D *>(obj);
  for(size_t i=0;i<n;i++)
  {
    o->fill(val[i], weight[i], error[i]);
  }
}
