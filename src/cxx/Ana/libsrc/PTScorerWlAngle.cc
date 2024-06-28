////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2022 Prompt developers                                     //
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

#include "PTScorerWlAngle.hh"
#include "PTActiveVolume.hh"

Prompt::ScorerWlAngle::ScorerWlAngle(const std::string &name, const Vector &samplePos, const Vector &refDir, double sourceSampleDist,
      double wl_min, double wl_max, unsigned wl_nbins, double angle_min, double angle_max, unsigned angle_nbins, ScorerType stype, int method, int scatnum)
:Scorer2D("ScorerWlAngle_"+name, stype, std::make_unique<Hist2D>("ScorerWlAngle_"+name, wl_min, wl_max, wl_nbins, angle_min, angle_max, angle_nbins)),
m_samplePos(samplePos), m_refDir(refDir), m_sourceSampleDist(sourceSampleDist), m_method(method), m_scatnum(scatnum)
{}

Prompt::ScorerWlAngle::~ScorerWlAngle() {}

void Prompt::ScorerWlAngle::score(Prompt::Particle &particle)
{
  if(m_scatnum==-1||particle.getNumScat()==m_scatnum)
  {
    double angle_cos = (particle.getPosition()-m_samplePos).angleCos(m_refDir);
    double angle = std::acos(angle_cos);
    if(particle.getPosition().x()<0) //default setting
      angle *= -1;
    if(m_method==0)
    {
      double wl = ekin2wl(particle.getEKin());
      m_hist->fill(wl, angle, particle.getWeight() );
    }
    else if(m_method==1) //static approximation
    {
      double dist = m_sourceSampleDist+(particle.getPosition()-m_samplePos).mag();
      double v = dist/particle.getTime();
      double ekin = 0.5*const_neutron_mass_evc2*v*v;
      double wl_ela = ekin2wl(ekin);
      m_hist->fill(wl_ela, angle, particle.getWeight());
    }

  }
}
