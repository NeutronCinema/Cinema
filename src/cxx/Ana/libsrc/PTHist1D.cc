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

#include "PTHist1D.hh"
#include "PTMath.hh"
#include "PTMCPLBinaryWrite.hh"
#include <typeinfo>
#include "PTUtils.hh"
#include "PTMCPLBinaryWrite.hh"

Prompt::Hist1D::Hist1D(const std::string &name, double xmin, double xmax, unsigned nbins, bool linear)
:HistBase(name, nbins), m_binfactor(0), m_linear(linear), m_logxmin(0)
{
  m_xmin=xmin, m_xmax=xmax, m_nbins=nbins;
  if(nbins==0)
    PROMPT_THROW(BadInput, "bin size is zero");

  if(xmin>=xmax)
    PROMPT_THROW2(BadInput, name << ": xmin should be smaller than xmax");

  if(linear) {
    m_binfactor=nbins/(xmax-xmin);
  }
  else {
    if(xmin<=0 || xmax<=0)
      PROMPT_THROW2(BadInput, name << ": xmin and xmax must be positive");
    m_binfactor=nbins/(log10(xmax)-log10(xmin));
    m_logxmin=log10(m_xmin);
  }
}

Prompt::Hist1D::~Hist1D()
{
}

std::vector<double> Prompt::Hist1D::getEdges() const
{
  if(m_linear)
    return linspace(m_xmin, m_xmax, m_nbins+1);
  else
    return logspace(log10(m_xmin), log10(m_xmax), m_nbins+1);
}

void Prompt::Hist1D::save(const std::string &filename) const
{
  //fixme: filename should be removed
  auto bwr = new MCPLBinaryWrite(m_mcpl_file_name);

  double intergral(getTotalWeight()), overflow(getOverflow()), underflow(getUnderflow());
  bwr->addHeaderComment(m_name);
  bwr->addHeaderComment(getTypeName(typeid(this)).c_str());
  bwr->addHeaderComment(("Total hit: " + std::to_string(getTotalHit())).c_str());

  bwr->addHeaderComment(("Integral weight: " + std::to_string(intergral )).c_str());
  bwr->addHeaderComment(("Accumulated weight: " + std::to_string(intergral-overflow-underflow)).c_str());
  bwr->addHeaderComment(("Overflow weight: " + std::to_string(overflow )).c_str());
  bwr->addHeaderComment(("Underflow weight: " + std::to_string(underflow)).c_str());

  bwr->addHeaderData("overflow", &overflow, {1}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("underflow", &underflow, {1}, Prompt::NumpyWriter::NPDataType::f8);

  bwr->addHeaderData("content", m_data.data(), {m_nbins}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("hit", m_hit.data(), {m_nbins}, Prompt::NumpyWriter::NPDataType::f8);
  bwr->addHeaderData("edge", getEdges().data(), {m_nbins+1}, Prompt::NumpyWriter::NPDataType::f8);

  char buffer [1000];
  int n =sprintf (buffer,
    "import numpy as np\nfrom Cinema.Prompt import PromptFileReader\n"
    "import matplotlib.pyplot as plt\n"
    "import argparse\n"
    "parser = argparse.ArgumentParser()\n"
    "parser.add_argument('-l', '--linear', action='store_true', dest='logscale', help='colour bar in log scale')\n"
    "args=parser.parse_args()\n"
    "f = PromptFileReader('%s.mcpl.gz')\n"
    "x=f.getData('edge')\n"
    "y=f.getData('content')\n"
    "if args.logscale:\n"
    "  plt.semilogy(x[:-1],y/np.diff(x), label=f'total weight={y.sum()}')\n"
    "else:\n"
    "  plt.plot(x[:-1],y/np.diff(x), label=f'total weight={y.sum()}')\n"
    "plt.grid()\n"
    "plt.legend()\n"
    "plt.show()\n", bwr->getFileName().c_str());

  delete bwr;
  std::ofstream outfile(filename+"_view.py");
  outfile << buffer;
  outfile.close();
}

//Normal filling:
void Prompt::Hist1D::fill(double val)
{
  fill(val, 1.);
}

void Prompt::Hist1D::fill(double val, double w)
{
  std::lock_guard<std::mutex> guard(m_hist_mutex);

  m_sumW+=w;
  if(val<m_xmin) {
    m_underflow += w;
    return;
  }
  else if(val>m_xmax) {
    m_overflow += w;
    return;
  }

  unsigned i = m_linear ? floor((val-m_xmin)*m_binfactor) : floor((log10(val)-m_logxmin)*m_binfactor) ;
  m_data[i] += w;
  m_hit[i] += 1;
  m_ww[i] += w*w;
}
