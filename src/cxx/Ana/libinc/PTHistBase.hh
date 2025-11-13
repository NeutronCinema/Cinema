#ifndef HistBase_hh
#define HistBase_hh

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

#include <string>
#include <cassert>
#include <vector>
#include <stdexcept>
#include <mutex>
#include "PTException.hh"

namespace Prompt {
  class HistBase {
  public:
    explicit HistBase(const std::string &name, unsigned nbins);
    virtual ~HistBase();

    virtual void merge(const HistBase &);
    void setWeight(double *data, size_t n);
    void setHit(double *data, size_t n);
    void setWW(double *data, size_t n);

    
    double getXMin() const {return m_xmin;}
    double getXMax() const {return m_xmax;}
    /**
     * @brief Get total weight.
     * 
     * Counting all, distinglished from HistBase::getAccWeight() const, 
     * which scores only those which falls between scorer variable range
     * 
     * @return double 
     */
    double getTotalWeight() const {return m_sumW;};
    double getOverflow() const {return m_overflow;};
    double getUnderflow() const {return m_underflow;};
    size_t getDataSize() const {return m_nbins;};

    void addNote(const std::string &note) {
      if(m_note!="")
      {
        m_note += ";";
        m_note += note;
      }
      else
        m_note = note;
    }
    const std::string& getNote() const {return m_note;}

    double getAccWeight() const {
      double sum(0);
      for(const auto v: m_data)
        sum += v;
      return sum;
    }

    double getTotalHit() const {
      double sum(0);
      for(const auto v: m_hit)
        sum += v;
      return sum;
    };

    void scale(double scalefact);
    void reset();

    const std::vector<double>& getRaw() const {return m_data;}
    const std::vector<double>& getHit() const {return m_hit;}
    const std::vector<double>& getww() const {return m_ww;}
    
    const std::string& getName() const {return m_name;}

    virtual unsigned dimension() const = 0;
    virtual void save(const std::string &filename) const = 0;

  protected:

    std::string m_name, m_note;
    mutable std::mutex m_hist_mutex;
    std::vector<double> m_data, m_hit, m_ww;
    double m_xmin;
    double m_xmax;
    double m_sumW;
    double m_underflow;
    double m_overflow;
    size_t m_nbins;
    std::string m_mcpl_file_name;

  private:
    //Copy/assignment are forbidden to avoid troubles
    // Move initialization
    HistBase(HistBase&& other) = delete;
    // Copy initialization
    HistBase(const HistBase& other) = delete;
    // Move assignment
    HistBase& operator = (HistBase&& other) = delete;
    // Copy assignment
    HistBase& operator = (const HistBase& other) = delete;

  };
}

#endif
