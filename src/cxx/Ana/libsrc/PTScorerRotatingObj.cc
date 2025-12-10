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

#include "PTScorerRotatingObj.hh"


Prompt::ScorerRotatingObj::ScorerRotatingObj(const std::string &name, const Vector &dir, const Vector &point,
  double rotFreq, unsigned int pdg)
:Scorer1D("ScorerRotatingObj_"+name, Scorer::ScorerType::PEA_POST,
  std::make_unique<Hist1D>("ScorerRotatingObj_"+name, 0, 1, 100), pdg),
  m_rotaxis(dir), m_point(point), m_angularfreq(2*M_PI*rotFreq)
{
  //fixme use m_rotaxis.normalise() to make sure the accuracy of the conversion
  if(!m_rotaxis.isUnitVector(1e-5))
    PROMPT_THROW(BadInput, "direction must be a unit vector");

}


Prompt::ScorerRotatingObj::~ScorerRotatingObj() {}

// The rational axis is parameterised as L(t) = A+tD, where A is a point on the
// axis, t is a factor, D is the direction.
// The closest line of point P to L is R,
// then t0 = D.(P-A)/(D.D), R = P-L(t0)
// In the case where D is a unit vector, and B = P-A
// R = (1-D.B)B
// velDir = RX
// the velocity at the point P is then 2\pi\omega R

Prompt::Vector Prompt::ScorerRotatingObj::getLinearVelocity(const Vector &pos)
{
  Vector B = pos - m_point;
  Vector R= m_rotaxis*(m_rotaxis.dot(B))-B;
  Vector dir = R.cross(m_rotaxis)*m_angularfreq;
  return dir;
}


void Prompt::ScorerRotatingObj::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;
  // when exiting Prompt::ActiveVolume::scoreExit sets the effdirection to null vector
  Vector vrot = getLinearVelocity(particle.getPosition());
  Vector labVel = particle.getDirection()* particle.calcSpeed();
  Vector comovingVel = labVel-vrot;
  double comovingSpeed = comovingVel.mag();
  double comvEkin = 0.5*comovingSpeed*comovingSpeed*particle.getMass();
  particle.setEffEKin(comvEkin);
  particle.setEffDirection(comovingVel.unit());
  m_hist->fill(comvEkin, particle.getWeight()*particle.getSurviveP());
}
