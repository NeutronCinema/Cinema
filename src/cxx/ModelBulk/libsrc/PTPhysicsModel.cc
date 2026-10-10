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

#include "PTPhysicsModel.hh"

Prompt::PhysicsBase::PhysicsBase(const std::string &name, int gdp,
             double emin, double emax)
 :m_modelName(name), m_modelvalid{gdp, emin, emax},
  m_oriented(false), m_rng(Singleton<SingletonPTRand>::getInstance()) {};

Prompt::PhysicsModel::PhysicsModel(const std::string &name, unsigned gdp,
             double emin, double emax)
:PhysicsBase(name, gdp, emin, emax), m_res()  { }


bool Prompt::PhysicsBase::isOriented()
{return m_oriented;}

double Prompt::PhysicsBase::getCrossSection(double ekin) const
{
  PROMPT_THROW(NotImplemented, "PhysicsBase::getCrossSection is not impletmented ")
  return 0.;
}

double Prompt::PhysicsBase::getCrossSection(double ekin, const Vector &dir) const
{
  PROMPT_THROW(NotImplemented, "PhysicsBase::getCrossSection is not impletmented ")
  return 0.;
}


Prompt::Vector Prompt::PhysicsBase::randIsotropicDirection() const
{
  //Very fast method (Marsaglia 1972) for generating points uniformly on the
  //unit sphere, costing approximately ~2.54 calls to rand->generate() and 1
  //call to sqrt().

  //Reference: Ann. Math. Statist. Volume 43, Number 2 (1972), 645-646.
  //           doi:10.1214/aoms/1177692644
  //Available at https://projecteuclid.org/euclid.aoms/1177692644

  double x0,x1,s;
  do {
    x0 = 2.0*m_rng.generate()-1.0;
    x1 = 2.0*m_rng.generate()-1.0;
    s = x0*x0 + x1*x1;
  } while (!s||s>=1);
  double t = 2.0*std::sqrt(1-s);
  return { x0*t, x1*t, 1.0-2.0*s };
}


Prompt::Vector Prompt::PhysicsBase::randDirectionGivenScatterMu( double mu, const Prompt::Vector& indir ) const
{
  pt_assert(std::abs(mu)<=1.);

  double m2 = indir.mag2();
  double invm = ( std::abs(m2-1.0)<1e-12 ? 1.0 : 1.0/std::sqrt(m2) );
  Vector u = indir * invm;

  //1) Create random unit-vector which is not parallel to indir:
  Vector tmpdir(0,0,0 );

  while (true) {
    tmpdir = randIsotropicDirection();
    double dotp = tmpdir.dot(u);
    double costh2 = dotp*dotp;//tmpdir is normalised vector
    //This cut is symmetric in the parallel plane => does not ruin final
    //phi-angle-flatness:
    if (costh2<0.99)
      break;
  }
  //2) Find ortogonal vector (the randomness thus tracing a circle on the
  //unit-sphere, once normalised)
  double xx = tmpdir.y()*u.z() - tmpdir.z()*u.y();
  double yy = tmpdir.z()*u.x() - tmpdir.x()*u.z();
  double zz = tmpdir.x()*u.y() - tmpdir.y()*u.x();
  double rm2 = xx*xx+yy*yy+zz*zz;

  //3) Use these two vectors to easily find the final direction (the
  //randomness above provides uniformly distributed azimuthal angle):
  double k = std::sqrt((1-mu*mu)/rm2);
  u *= mu;
  return { u.x()+k*xx, u.y()+k*yy, u.z()+k*zz };
}

  
