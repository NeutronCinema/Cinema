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

#include "PTPluginTypes.hh"
#include "PTException.hh"
#include "PTUtils.hh"

namespace Prompt::Plugin {

CfgView::CfgView(std::string raw)
: m_raw(std::move(raw))
{
  // The host only dispatches to the registry after CfgParser accepted the
  // string, so this parse cannot fail in practice; a lenient fallback keeps
  // direct CfgView users safe.
  try
  {
    m_parsed = Singleton<CfgParser>::getInstance().parse(m_raw);
    m_parsed.getStringIfExist("physics", m_ns);
    // Host-reserved keys are consumed by the host (ParticleProcess) and
    // never surface to a factory: a plugin cannot scatter_bias or override
    // its own density.
    for(const char *reserved : {"physics", "scatter_bias", "abs_bias", "absorp_in_weight", "density"})
      m_parsed.parameters.erase(reserved);
  }
  catch (const Error::Exception&)
  {
    m_parsed = CfgParser::StringCfg();
  }
}

bool CfgView::has(const char* key) const
{
  return m_parsed.contains(key);
}

std::string CfgView::str(const char* key) const
{
  std::string out;
  if(!m_parsed.getStringIfExist(key, out))
    PROMPT_THROW2(BadInput, "physics=" << m_ns << ": missing required key '" << key << "'");
  return out;
}

std::string CfgView::strOr(const char* key, const char* dflt) const
{
  std::string out;
  if(m_parsed.getStringIfExist(key, out))
    return out;
  return std::string(dflt);
}

double CfgView::number(const char* key) const
{
  std::string text;
  if(!m_parsed.getStringIfExist(key, text))
    PROMPT_THROW2(BadInput, "physics=" << m_ns << ": missing required key '" << key << "'");
  try
  {
    return ptstod(text);
  }
  catch (const std::exception&)
  {
    PROMPT_THROW2(BadInput, "physics=" << m_ns << ": key '" << key
                  << "' is not a number: '" << text << "'");
  }
}

std::vector<std::string> CfgView::keys() const
{
  std::vector<std::string> out;
  out.reserve(m_parsed.parameters.size());
  for(const auto &pr : m_parsed.parameters)
    out.push_back(pr.first);
  return out;
}

}
