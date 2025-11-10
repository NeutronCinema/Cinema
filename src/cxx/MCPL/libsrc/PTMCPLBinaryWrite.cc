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

#include "mcpl.h"
#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
#include "PTMCPLBinaryWrite.hh"


Prompt::MCPLBinaryWrite::MCPLBinaryWrite(const std::string &fn, bool enable_double,  bool enable_extra3double, bool enable_extraUnsigned)
:MCPLBinary(fn), m_fileCreated(true), m_headerClosed(false) 
{ 
   m_using_double = enable_double;
   m_with_extra3double = enable_extra3double;
   m_with_extraUserUnsigned = enable_extraUnsigned; 
   m_file = mcpl_create_outfile(fn.c_str());
}

void Prompt::MCPLBinaryWrite::init()
{
  m_fileCreated = false;
  mcpl_hdr_set_srcname(m_file,"Prompt");
  if(m_using_double) mcpl_enable_doubleprec(m_file);
  if(m_with_extra3double)   mcpl_enable_polarisation(m_file);  // double[3]
  if(m_with_extraUserUnsigned)  mcpl_enable_userflags(m_file);    // uint32_t

  mcpl_hdr_set_srcname(m_file, ("Prompt " + PTVersion).c_str());  //set data source name
  m_particleInFile = mcpl_get_empty_particle(m_file);
}

Prompt::MCPLBinaryWrite::~MCPLBinaryWrite()
{
    if(!m_fileCreated)
      // mcpl_close_outfile(m_file);
      mcpl_closeandgzip_outfile(m_file); // fixme: should provide option to gzip
}

void Prompt::MCPLBinaryWrite::addHeaderComment(const std::string &comment)
{
  if(m_fileCreated) init();
  if(m_headerClosed)
      PROMPT_THROW(LogicError, "addHeaderComment can not operate on a file when the file header is closed ");

  mcpl_hdr_add_comment(m_file, comment.c_str());
}

void Prompt::MCPLBinaryWrite::write(const PromptRecord &p)
{
  if(m_fileCreated) init();
  m_headerClosed=true;

  //size 12 double, a 32-bit int and a 32-bit unsigned
  // 8*12+4*2=104
  memcpy ( m_particleInFile, &(p.mcplParticle), sizeof(*m_particleInFile));
  mcpl_add_particle(m_file, m_particleInFile);
}

void Prompt::MCPLBinaryWrite::write(const mcpl_particle_t &p)
{
  if(m_fileCreated) init();
  m_headerClosed=true;
  
  memcpy (m_particleInFile, &p, sizeof(mcpl_particle_t));
  mcpl_add_particle(m_file, m_particleInFile);
}


void Prompt::MCPLBinaryWrite::write(const Particle &p)
{
  if(m_fileCreated) init();

  m_headerClosed=true;
  m_particleInFile->pdgcode = p.getPDG();

  //position in centimeters:
  const Vector &pos = p.getPosition();
  m_particleInFile->position[0] = pos.x()*0.1;
  m_particleInFile->position[1] = pos.y()*0.1;
  m_particleInFile->position[2] = pos.z()*0.1;

  //kinetic energy in MeV:
  m_particleInFile->ekin = p.getEKin()*1e-6;

  const Vector &dir = p.getDirection();

  m_particleInFile->direction[0] = dir.x();
  m_particleInFile->direction[1] = dir.y();
  m_particleInFile->direction[2] = dir.z();

  //time in milliseconds:
  m_particleInFile->time = p.getTime()*1e3;

  //weight in unspecified units:
  m_particleInFile->weight = p.getWeight();

  //modify userflags (unsigned_32) and polarisation (double[3]) as well, if enabled.
  if(m_with_extraUserUnsigned)
    m_particleInFile->userflags = p.getEventID();

  mcpl_add_particle(m_file, m_particleInFile);
}
