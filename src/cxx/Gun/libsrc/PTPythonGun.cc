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

#include "PTPythonGun.hh"
#include "PTNeutron.hh"
#include "PTGamma.hh"
#include "PTPython.hh"

Prompt::PythonGun::PythonGun(int pdg)
    : PrimaryGun(Particle(pdg)), m_stackManager(Singleton<StackManager>::getInstance())
{  
}

Prompt::PythonGun::~PythonGun()
{ 
}


void Prompt::PythonGun::pushToStack(double *pdata)
{
    m_ekin = pdata[0];
    m_weight = pdata[1];
    m_time = pdata[2];
    m_pos.x() = pdata[3];
    m_pos.y() = pdata[4];
    m_pos.z() = pdata[5];
    m_dir.x() = pdata[6];
    m_dir.y() = pdata[7];
    m_dir.z() = pdata[8];

    m_ekin0=m_ekin;
    m_eventid++;
    m_alive = true;
    m_stackManager.add(std::make_unique<Particle>(*this));
}

void* pt_PythonGun_new(int pdg)
{
    return static_cast<void *> (new Prompt::PythonGun(pdg)) ; 
}

void pt_PythonGun_delete(void *obj)
{
    delete static_cast<Prompt::PythonGun *> (obj);
}

void pt_PythonGun_pushToStack(void *obj, double *pdata)
{
    static_cast<Prompt::PythonGun *> (obj)->pushToStack(pdata);
}

void pt_PythonGun_pushToStackMany(void *obj, double *pdata, unsigned num)
{
    for(unsigned i=0;i<num;i++)
    {
        static_cast<Prompt::PythonGun *> (obj)->pushToStack(pdata + i*9);
    }
}
