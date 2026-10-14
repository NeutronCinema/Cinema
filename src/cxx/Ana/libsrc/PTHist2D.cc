////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    //
//                                                                            //
//  Copyright 2021-2026 Cinema developers                                     //
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

#include "PTHist2D.hh"
#include "PTMath.hh"
#include "PTMCPLBinaryWrite.hh"
#include <typeinfo>
#include "PTUtils.hh"
#include "PTMCPLBinaryWrite.hh"

Prompt::Hist2D::Hist2D(const std::string &name, double xmin, double xmax, unsigned xnbins,
                       double ymin, double ymax, unsigned ynbins)
:HistBase(name, xnbins*ynbins), m_xbinfactor(xnbins/(xmax-xmin)),
m_ybinfactor(ynbins/(ymax-ymin))
{
  m_xmin=xmin, m_xmax=xmax, m_xnbins=xnbins;
  m_ymin=ymin, m_ymax=ymax, m_ynbins=ynbins;
  m_nbins = m_xnbins * m_ynbins;

  if(xnbins*ynbins==0)
    PROMPT_THROW(BadInput, "bin size is zero");

  if(xmax<=xmin || ymax<=ymin)
    PROMPT_THROW(BadInput, "max<min");

}

Prompt::Hist2D::~Hist2D()
{
}

void Prompt::Hist2D::operator+=(const Hist2D& hist)
{
  auto data=hist.getRaw();
  if(data.size()!=m_data.size())
    PROMPT_THROW(BadInput, "operator+= hist with different data size");
  std::lock_guard<std::mutex> guard(m_hist_mutex);
  for(unsigned i=0;i<data.size();++i)
    m_data[i]+=data[i];
}

std::vector<double> Prompt::Hist2D::getXEdge() const
{
  return linspace(m_xmin, m_xmax, m_xnbins+1);
}

std::vector<double> Prompt::Hist2D::getYEdge() const
{
  return linspace(m_ymin, m_ymax, m_ynbins+1);
}


void Prompt::Hist2D::save(const std::string &filename) const
{
  //fixme: filename should be removed
  std::cout << "saving 2d\n";
  auto bwr = new MCPLBinaryWrite(m_mcpl_file_name);
  double intergral(getTotalWeight()), overflow(getOverflow()), underflow(getUnderflow());
  bwr->addHeaderComment(m_name);
  bwr->addHeaderComment(getTypeName(typeid(this)).c_str());
  bwr->addHeaderComment(("Total hit: " + std::to_string(getTotalHit())).c_str());

  bwr->addHeaderComment(("Integral weight: " + std::to_string(intergral )).c_str());
  bwr->addHeaderComment(("Accumulated weight: " + std::to_string(intergral-overflow-underflow)).c_str());
  bwr->addHeaderComment(("Overflow weight: " + std::to_string(overflow )).c_str());
  bwr->addHeaderComment(("Underflow weight: " + std::to_string(underflow)).c_str());

  bwr->addHeaderData("Overflow", &overflow, {1}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("Underflow", &underflow, {1}, Prompt::NumpyWriter::NPDataType::f8);

  bwr->addHeaderData("content", m_data.data(), {m_xnbins, m_ynbins}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("hit", m_hit.data(), {m_xnbins, m_ynbins}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("xedge", getXEdge().data(), {m_xnbins+1}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("yedge", getYEdge().data(), {m_ynbins+1}, Prompt::NumpyWriter::NPDataType::f8);

  char buffer [2000];
  //fixme: add xy to dimansion
  int n =sprintf (buffer,
    "from Cinema.Prompt import PromptFileReader\n"
    "import matplotlib.pyplot as plt\n"
    "import matplotlib.colors as colors\nimport numpy as np\n"
    "import argparse\nparser = argparse.ArgumentParser()\n"
    "parser.add_argument('-l', '--linear', action='store_true', dest='logscale', help='colour bar in log scale')\n"
    "f = PromptFileReader('%s.mcpl.gz')\n"
    "args=parser.parse_args()\n"
    "data=f.getData('content')\n"
    "count=f.getData('hit')\n"
    "x=f.getData('xedge'); y=f.getData('yedge'); X, Y = np.meshgrid(x, y)\n"
    "fig=plt.figure()\n"
    "ax = fig.add_subplot(111)\n"
    "if args.logscale:\n"
    "  pcm = ax.pcolormesh(X, Y, data.T, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=data.max()*1e-10, vmax=data.max()), shading='auto')\n"
    "else:\n"
    "  pcm = ax.pcolormesh(X, Y, data.T, cmap=plt.cm.jet,shading='auto')\n"
    "fig.colorbar(pcm, ax=ax)\n"
    "count=count.sum()\n"
    "integral= data.sum()\n"
    "plt.title(f'%s, integral {integral}, count {count}')\n"
    "plt.figure()\n"
    "plt.subplot(211)\n"
    "plt.plot(x[:-1]+np.diff(x)*0.5, data.sum(axis=1))\n"
    "plt.xlabel('integral x')\n"
    "plt.title('%s')\n"
    "plt.subplot(212)\n"
    "plt.plot(y[:-1]+np.diff(y)*0.5, data.sum(axis=0))\n"
    "plt.xlabel('integral y')\n"
    "plt.show()\n", bwr->getFileName().c_str(), bwr->getFileName().c_str(), bwr->getFileName().c_str());

  delete bwr;
  std::ofstream outfile(filename+"_view.py");
  outfile << buffer;
  outfile.close();

}

//Normal filling:
void Prompt::Hist2D::fill(double xval, double yval)
{
  fill(xval, yval, 1.);
}

void Prompt::Hist2D::fill(double xval, double yval, double w)
{
  fill_unguard(xval, yval, w);
}

void Prompt::Hist2D::merge(const Prompt::HistBase &hist)
{
  auto &ref = dynamic_cast<const Prompt::Hist2D&>(hist);

  if(m_xbinfactor!=ref.m_xbinfactor)
    PROMPT_THROW2(CalcError, "m_xbinfactor " << m_xbinfactor << " is different with the m_xbinfactor of another histogram " << ref.m_xbinfactor);

  if(m_ybinfactor!=ref.m_ybinfactor)
    PROMPT_THROW2(CalcError, "m_ybinfactor " << m_ybinfactor << " is different with the m_ybinfactor of another histogram " << ref.m_ybinfactor);

  if(m_ymin!=ref.m_ymin)
    PROMPT_THROW2(CalcError, "m_ymin " << m_ymin << " is different with the m_ymin of another histogram " << ref.m_ymin);

  if(m_ymax!=ref.m_ymax)
    PROMPT_THROW2(CalcError, "m_ymax " << m_ymax << " is different with the m_ymax of another histogram " << ref.m_ymax);

  if(m_xnbins!=ref.m_xnbins)
    PROMPT_THROW2(CalcError, "m_xnbins " << m_xnbins << " is different with the m_xnbins of another histogram " << ref.m_xnbins);

  if(m_ynbins!=ref.m_ynbins)
    PROMPT_THROW2(CalcError, "m_ynbins " << m_ynbins << " is different with the m_ynbins of another histogram " << ref.m_ynbins);

  HistBase::merge(hist);

}
