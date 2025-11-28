#ifndef Prompt_Particale_hh
#define Prompt_Particale_hh

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

#include "PTVector.hh"
#include "PTMath.hh"
#include "PTUnitSystem.hh"
#include <ostream>

//! Particle pgd code is zero by default.  neutron(2112). Proton (2212) is also supported.
//! fixme: support Gamma (22) as well.
namespace Prompt {

  class Particle {
    friend class PrimaryGun;

  public:
    enum class KillType {ABSORB, BIAS, SCORE, RT_ABSORB };
  public:
    Particle(int pdg=const_neutron_pgd);
    Particle(double ekin, const Vector& dir, const Vector& pos, int pdg=const_neutron_pgd);
    Particle(const Particle& p);

    virtual ~Particle(){};

    void moveForward(double length);

    void setDirection(const Vector& dir);
    const Vector &getDirection() const { return m_dir; }

    bool hasEffEnergy() const { return !m_effdir.isStrictNullVector(); }
    double getEffEKin() const { return m_effekin; }
    void setEffEKin(double e)  { m_effekin=e; }
    virtual void setEffDirection(const Vector& dir);
    const Vector &getEffDirection() const { return m_effdir; }

    void setPosition(const Vector& pos);
    const Vector &getPosition() const { return m_pos; }

    double getTime() const { return m_time; }
    void setTime(double time) { m_time =time; }

    void setWeight(double w) { m_weight=w; }


    double getStep() const { return m_step; }
    double getEnergyChange() const { return m_deltaEn; }
    void setEKin(double ekin);
    double getEKin() const { return m_ekin; }
    double getEKin0() const { return m_ekin0; }
    double getWeight() const { return m_weight; }
    void scaleWeight(double factor) { m_weight *= factor; }
    unsigned long long getEventID() const { return m_eventid; }
    KillType getKillType() const { return m_killtype; }

    void kill(KillType t);
    bool isAlive();

    int getPDG() const { return m_pdg; }

    virtual double calcSpeed() const;
    virtual double calcEffSpeed() const;

    double getMass() const { return m_rest_mass; }

    double getDeposition() const { return m_deposition; }
    void setDeposition(double e) { m_deposition=e; }

    double getAbsP() const { return m_absP; }
    void scaleAbsP(double scale) { m_absP*= scale;}

    friend std::ostream& operator << (std::ostream &, const Particle&);

  protected:
    Vector m_dir, m_pos;
    double m_ekin0, m_ekin, m_time;
    double m_weight, m_absP;
    double m_rest_mass;
    unsigned long long m_eventid, m_id, m_parentid;
    int m_pdg;
    KillType m_killtype;
    bool m_alive;

    // to be remove
    double m_step, m_deltaEn, m_deposition;

    // for Doppler models
    Vector m_effdir; 
    double m_effekin;
  };

  std::ostream& operator << (std::ostream &, const Particle&);
}


inline Prompt::Particle::Particle(int pdg)
  :m_ekin0(0.), m_ekin(0.), m_effekin(0.), m_time(0.), m_dir(), m_effdir(), m_pos(), m_pdg(pdg),
  m_weight(1.), m_absP(1.), m_rest_mass(0.), m_alive(true), m_eventid(0), m_id(0), m_parentid(0),
  m_step(0.), m_deltaEn(0.), m_deposition(0.)
{
  if(m_pdg == const_neutron_pgd)
    m_rest_mass = const_neutron_mass_evc2;
}

inline Prompt::Particle::Particle(double ekin, const Vector& dir, const Vector& pos, int pdg)
  :m_ekin0(ekin), m_ekin(ekin), m_effekin(0.), m_time(0.), m_dir(dir), m_effdir(), m_pos(pos), m_pdg(pdg),
  m_weight(1.), m_absP(1.), m_rest_mass(0), m_alive(true), m_eventid(0), m_id(0), m_parentid(0),
  m_step(0.), m_deltaEn(0.), m_deposition(0.)
{
  if(m_pdg == const_neutron_pgd)
    m_rest_mass = const_neutron_mass_evc2;

  m_dir.normalise();
}

inline Prompt::Particle::Particle(const Particle& p)
{
  *this = p;
}

inline void Prompt::Particle::moveForward(double length)
{
  m_step = length;
  m_deposition = 0.;
  if (length) {
    m_pos += m_dir*length;
    m_time += length/calcSpeed();
  }
}

inline void Prompt::Particle::setEKin(double ekin)
{
  m_deltaEn = m_ekin - ekin;
  m_ekin = ekin;
}

inline void Prompt::Particle::setPosition(const Vector& pos)
{
  m_pos = pos;
}

inline void Prompt::Particle::setEffDirection(const Vector& dir)
{
  m_effdir = dir;
}

inline void Prompt::Particle::setDirection(const Vector& dir)
{
  m_dir = dir;
}

inline double Prompt::Particle::calcSpeed() const
{
    return m_rest_mass ? std::sqrt(2*m_ekin/m_rest_mass) : const_c;
}

inline double Prompt::Particle::calcEffSpeed() const
{
  return m_rest_mass ? std::sqrt(2*m_effekin/m_rest_mass) : const_c;
}

inline bool Prompt::Particle::isAlive()
{
  return m_alive;
}

#endif
