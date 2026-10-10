#ifndef Prompt_Exception_hh
#define Prompt_Exception_hh

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

#include <stdexcept>
#include <sstream>
#include <string>

namespace Prompt {

  namespace Error {

    class Exception : public std::runtime_error {
    public:
      explicit Exception(const std::string& msg, const char * f, unsigned l) throw();
      explicit Exception(const char * msg,  const char * f, unsigned l) throw();
      virtual const char * getTypeName() const throw() = 0;
      const char * getFile() const throw() { return m_file; }
      unsigned getLineNo() const throw() { return m_lineno; }
      Exception( const Exception & o ) throw();
      Exception & operator= ( const Exception & o ) throw();
      virtual ~Exception() throw();
    private:
      const char * m_file;
      unsigned m_lineno;
    };

#define PROMPT_ADD_ERROR_TYPE(ErrType)                                                               \
    struct ErrType : public Exception {                                                                \
      explicit ErrType(const std::string& msg, const char * f, unsigned l) throw() : Exception(msg,f,l) {} \
      explicit ErrType(const char * msg,  const char * f, unsigned l) throw() : Exception(msg,f,l) {}      \
      virtual const char * getTypeName() const throw() { return #ErrType; }                            \
      virtual ~ErrType() throw();                                                                      \
    }
    //List of error types (destructors implemented in .cc):
    PROMPT_ADD_ERROR_TYPE(FileNotFound);
    PROMPT_ADD_ERROR_TYPE(DataLoadError);
    PROMPT_ADD_ERROR_TYPE(MissingInfo);
    PROMPT_ADD_ERROR_TYPE(CalcError);
    PROMPT_ADD_ERROR_TYPE(LogicError);
    PROMPT_ADD_ERROR_TYPE(BadInput);
    PROMPT_ADD_ERROR_TYPE(NotImplemented);
#undef Prompt_ADD_ERROR_TYPE
  }
}

/////////////////////////////////////////////////////////////////////////////////////////////
//                                                                                         //
// Macro's for easy and consistent throwing from within Prompt code (don't use THROW2      //
// in tight CPU-critical code):                                                            //
//                                                                                         //
//   NPrompt_THROW(ErrType,"some hardcoded message")                                       //
//   NPrompt_THROW2(ErrType,"some "<<flexible<<" message")                                 //
//                                                                                         //
/////////////////////////////////////////////////////////////////////////////////////////////

#define PROMPT_THROW(ErrType, msg)                            \
  {                                                           \
    throw ::Prompt::Error::ErrType(msg,__FILE__,__LINE__);    \
  }

#define PROMPT_THROW2(ErrType, msg)       \
  {                                       \
    std::ostringstream err_oss;           \
    err_oss << msg;                       \
    PROMPT_THROW(ErrType,err_oss.str())   \
  }

//Custom pt_assert which throws LogicErrors in dbg builds; pt_assert2
//avoids unused variable warnings in opt builds; pt_assert_always is
//enabled in all builds. Note that since these assert's throw, they
//should not be used in destructors.
#define prompt_str(s) #s
#define prompt_xstr(s) prompt_str(s)
#define pt_assert_always(x) do { if (!(x)) { PROMPT_THROW(LogicError,\
                              "Assertion failure: " prompt_xstr(x)); } } while(0)

#ifndef NDEBUG
#  define pt_assert(x) pt_assert_always(x)
#  define pt_assert2(x) pt_assert_always(x)
#else
#  define pt_assert(x) do {} while(0)
#  define pt_assert2(x) do { (void)sizeof(x); } while(0)//use but dont evaluate x
#endif

#define pt_not_implemented do { Prompt_THROW(LogicError, "NotImplemented") } while(0)
#endif
