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

// Prompt::Error exception hierarchy: throwing macros, message content, specific
// versus base catching, and copy/assignment propagation of message, file and line.

#include "../doctest.h"

#include "PTException.hh"

#include <cstring>
#include <stdexcept>
#include <string>

namespace pt = Prompt;

TEST_CASE("exception_catchable_as_base_types")
{
  // the PROMPT_THROW macro throws the concrete type ...
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "bad input for test"); }(),
                  pt::Error::BadInput);
  // ... which is a Prompt::Error::Exception ...
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "bad input for test"); }(),
                  pt::Error::Exception);
  // ... and a std::runtime_error
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "bad input for test"); }(),
                  std::runtime_error);
}

TEST_CASE("exception_message_and_origin")
{
  try {
    PROMPT_THROW(MissingInfo, "required key missing");
    CHECK_MESSAGE(false, "the exception must escape");
  } catch (const pt::Error::Exception &e) {
    CHECK(std::string(e.what()).find("required key missing") != std::string::npos);
    CHECK(e.what() == std::string("required key missing"));
    CHECK(std::string(e.getTypeName()) == "MissingInfo");
    // __FILE__/__LINE__ of the throw site are recorded
    CHECK(e.getLineNo() > 0);
    CHECK(std::string(e.getFile()).find("test_exceptions.cc") != std::string::npos);
  }
}

TEST_CASE("throw2_streams_into_message")
{
  try {
    int value = 42;
    PROMPT_THROW2(CalcError, "value " << value << " out of range");
    CHECK_MESSAGE(false, "the exception must escape");
  } catch (const pt::Error::CalcError &e) {
    CHECK(e.what() == std::string("value 42 out of range"));
  }
  // floating point values stream with default formatting
  CHECK_THROWS_AS([] { PROMPT_THROW2(LogicError, "x=" << 2.5 << " invalid"); }(),
                  pt::Error::LogicError);
  try {
    PROMPT_THROW2(LogicError, "x=" << 2.5 << " invalid");
  } catch (const pt::Error::Exception &e) {
    CHECK(std::string(e.what()).find("x=2.5 invalid") != std::string::npos);
  }
}

TEST_CASE("derived_types_catch_polymorphic")
{
  // specific catch works for every registered error type ...
  CHECK_THROWS_AS([] { PROMPT_THROW(NotImplemented, "not implemented"); }(),
                  pt::Error::NotImplemented);
  CHECK_THROWS_AS([] { PROMPT_THROW(CalcError, "calc failed"); }(),
                  pt::Error::CalcError);
  // ... while the base handler still receives them with the right type name
  try {
    PROMPT_THROW(NotImplemented, "not implemented");
  } catch (const pt::Error::Exception &e) {
    CHECK(std::string(e.getTypeName()) == "NotImplemented");
  }
  try {
    PROMPT_THROW(CalcError, "calc failed");
  } catch (const pt::Error::Exception &e) {
    CHECK(std::string(e.getTypeName()) == "CalcError");
  }
}

TEST_CASE("exception_copy_preserves_message_and_origin")
{
  pt::Error::BadInput orig(std::string("original message"), "somefile.hh", 77u);
  pt::Error::BadInput copy(orig);
  CHECK(std::string(copy.what()) == "original message");
  CHECK(std::string(copy.getFile()) == "somefile.hh");
  CHECK(copy.getLineNo() == 77u);
  CHECK(std::string(copy.getTypeName()) == "BadInput");

  // copy through a base reference keeps everything (no slicing of the dynamic type)
  const pt::Error::Exception &asBase = orig;
  pt::Error::BadInput copy2(static_cast<const pt::Error::BadInput &>(asBase));
  CHECK(std::string(copy2.what()) == "original message");
  CHECK(copy2.getLineNo() == 77u);
  CHECK(std::string(copy2.getFile()) == "somefile.hh");
}

TEST_CASE("exception_assignment_preserves_message")
{
  pt::Error::CalcError dst(std::string("first"), "f1.cc", 1u);
  pt::Error::CalcError src(std::string("second message"), "f2.cc", 22u);
  dst = src;
  CHECK(std::string(dst.what()) == "second message");
  CHECK(std::string(dst.getFile()) == "f2.cc");
  CHECK(dst.getLineNo() == 22u);
  CHECK(std::string(dst.getTypeName()) == "CalcError");
  // the source object is untouched
  CHECK(std::string(src.what()) == "second message");
  CHECK(src.getLineNo() == 22u);
}
