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

#include "PTGeoTranslator.hh"
#include <cstring>

Prompt::GeoTranslator::GeoTranslator()
:m_trans()
{
}

Prompt::GeoTranslator::~GeoTranslator()
{
}

Prompt::Vector Prompt::GeoTranslator::global2Local(const Prompt::Vector& glo) const
{
  auto loc = m_trans.InverseTransform(*reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&glo));
  return *reinterpret_cast<const Prompt::Vector*>(&loc);
}

Prompt::Vector Prompt::GeoTranslator::local2Global(const Prompt::Vector& loc) const
{
  auto glo = m_trans.Transform(*reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&loc));
  return *reinterpret_cast<const Prompt::Vector*>(&glo);
}

Prompt::Vector Prompt::GeoTranslator::global2Local_direction(const Prompt::Vector&glo_dir) const
{
  auto loc_dir = m_trans.InverseTransformDirection(*reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&glo_dir));
  return *reinterpret_cast<const Prompt::Vector*>(&loc_dir);
}

Prompt::Vector Prompt::GeoTranslator::local2Global_direction(const Prompt::Vector& loc_dir) const
{
  auto glo_dir = m_trans.TransformDirection(*reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&loc_dir));
  return *reinterpret_cast<const Prompt::Vector*>(&glo_dir);
}
