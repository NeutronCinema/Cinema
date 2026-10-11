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

// Second CfgParser coverage file: extends test_cfgparser.cc with quoting
// corner cases (multiple/empty/non-first quoted sections, the placeholder
// mechanism), '='-in-value rejection, non-standard keys ('#', whitespace),
// numeric coercion semantics, long inputs and a parse/re-parse round trip.
// All expectations pin the actual (current) behaviour of
// Prompt::CfgParser::parse, including its documented quirks.

#include "../doctest.h"

#include "PTCfgParser.hh"
#include "PTSingleton.hh"
#include "PTUtils.hh"
#include "PTVector.hh"

#include <string>

namespace pt = Prompt;

// Helper: parse through the CfgParser singleton (private constructor).
static pt::CfgParser::StringCfg parseCfg(const std::string& str)
{
  return pt::Singleton<pt::CfgParser>::getInstance().parse(str);
}

TEST_CASE("CfgParser quoted section in non-first position")
{
  // quoting is resolved before splitting, so it works in any section
  auto cfg = parseCfg("k=v;q='a;b'");
  CHECK(cfg.size() == 2);
  CHECK(cfg.name == "k=v");
  CHECK(cfg.find("k") == "v");
  CHECK(cfg.find("q") == "a;b");
}

TEST_CASE("CfgParser empty quoted value: present in map but finds as empty")
{
  auto cfg = parseCfg("a='';b=c");
  CHECK(cfg.size() == 2);          // the section itself is well defined
  CHECK(cfg.find("a").empty());    // value is the empty string ...
  CHECK_FALSE(cfg.contains("a"));  // ... so contains() reports false
  CHECK(cfg.find("b") == "c");
}

TEST_CASE("CfgParser quoted value keeps all interior whitespace")
{
  // double spaces survive quoting (they would be collapsed unquoted)
  auto cfg = parseCfg("a = 'hello  world' ; b=c");
  CHECK(cfg.size() == 2);
  CHECK(cfg.find("a") == "hello  world");
  CHECK(cfg.find("b") == "c");
}

TEST_CASE("CfgParser placeholder mechanism: magic-substring values are hijacked")
{
  // quoted substrings are parked under a "magicsubstring<i>" placeholder and
  // substituted back by exact value match afterwards - a literal value that
  // collides with the placeholder of another section is replaced as well
  auto cfg = parseCfg("a=magicsubstring0;b='z'");
  CHECK(cfg.find("a") == "z");
  CHECK(cfg.find("b") == "z");
  // without a quoted section the literal survives untouched
  auto plain = parseCfg("a=magicsubstring0");
  CHECK(plain.find("a") == "magicsubstring0");
  // the cfg name is captured after placeholder substitution of the first
  // section, so quoted first sections leave the placeholder in the name
  auto named = parseCfg("q='v';k2=w2");
  CHECK(named.name == "q=magicsubstring0");
  CHECK(named.find("q") == "v");
  CHECK(named.find("k2") == "w2");
}

TEST_CASE("CfgParser more than one quoted section per string is not supported")
{
  // positions of subsequent quote pairs are stale after the first in-place
  // replacement, so a second quoted section is not substituted: here the
  // quotes survive and the section no longer splits into exactly key=value
  bool caught = false;
  try {
    parseCfg("a='x;y';b='p=q';c=r");
  } catch (const Prompt::Error::BadInput& e) {
    caught = true;
    CHECK(std::string(e.what()).find("ill-defined") != std::string::npos);
    CHECK(std::string(e.what()).find("b='p=q'") != std::string::npos);
  }
  CHECK(caught);
}

TEST_CASE("CfgParser unquoted '=' inside a value is rejected")
{
  // split() yields more than two tokens when the value itself contains '='
  REQUIRE_THROWS_AS(parseCfg("url=http://a?b=c"), Prompt::Error::BadInput);
  // newlines are just whitespace: removing them glues both halves together
  REQUIRE_THROWS_AS(parseCfg("a=b\nc=d"), Prompt::Error::BadInput);
  // quoting is the supported escape hatch
  CHECK_NOTHROW(parseCfg("url='http://a?b=c'"));
}

TEST_CASE("CfgParser '#' starts no comment: sections become keys or throw")
{
  // a '#' section carrying '=' is parsed as a regular (odd-looking) key
  auto cfg = parseCfg("a=b;#note=hi");
  CHECK(cfg.size() == 2);
  CHECK(cfg.find("#note") == "hi");
  CHECK(cfg.find("a") == "b");
  // without '=' the "comment" section is ill-defined like any other
  bool caught = false;
  try {
    parseCfg("a=b;# just a comment");
  } catch (const Prompt::Error::BadInput& e) {
    caught = true;
    CHECK(std::string(e.what()).find("#justacomment") != std::string::npos);
  }
  CHECK(caught);
}

TEST_CASE("CfgParser whitespace-only sections are dropped, keys are whitespace-free")
{
  auto cfg = parseCfg("a=b; ; ;c=d");
  CHECK(cfg.size() == 2);
  CHECK(cfg.find("a") == "b");
  CHECK(cfg.find("c") == "d");

  auto tabs = parseCfg("a=b;\t;\tc=d");
  CHECK(tabs.size() == 2);

  // whitespace inside a key is stripped exactly like inside values
  auto keyed = parseCfg("my key = v");
  CHECK(keyed.size() == 1);
  CHECK(keyed.name == "mykey=v");
  CHECK(keyed.find("mykey") == "v");
  CHECK_FALSE(keyed.contains("my key"));
}

TEST_CASE("CfgParser keys are case sensitive, duplicate keys: last wins (typed)")
{
  auto cased = parseCfg("Key=1;key=2");
  CHECK(cased.size() == 2);
  CHECK(cased.find("Key") == "1");
  CHECK(cased.find("key") == "2");

  auto dup = parseCfg("n=1;n=2;n=3");
  CHECK(dup.size() == 1);
  CHECK(dup.find("n") == "3");
  double d = 0.;
  CHECK(dup.getDoubleIfExist("n", d));
  CHECK(d == doctest::Approx(3.0));

  auto dupvec = parseCfg("v=1,1,1;v=9,8,7");
  CHECK(dupvec.size() == 1);
  pt::Vector v;
  CHECK(dupvec.getVectorIfExist("v", v));
  CHECK(v.x() == doctest::Approx(9.0));
  CHECK(v.y() == doctest::Approx(8.0));
  CHECK(v.z() == doctest::Approx(7.0));
}

TEST_CASE("CfgParser numeric coercion: int getters prefix-parse like std::stoi")
{
  auto cfg = parseCfg("i1=42.9;i2=1e3;i3=0x10;i4=-7;d1=2.5abc;d2=42;u1=3.9;u2=-5;"
                      "b1=-1;b2=on;b3=1e-3");
  int i = 0;
  CHECK(cfg.getIntIfExist("i1", i));
  CHECK(i == 42);  // std::stoi truncates
  CHECK(cfg.getIntIfExist("i2", i));
  CHECK(i == 1);   // NOT 1000: prefix parse stops at 'e' (no scientific ints)
  CHECK(cfg.getIntIfExist("i3", i));
  CHECK(i == 0);   // NOT 16: prefix parse stops at 'x' (no hex)
  CHECK(cfg.getIntIfExist("i4", i));
  CHECK(i == -7);

  double d = 0.;
  CHECK(cfg.getDoubleIfExist("d1", d));
  CHECK(d == doctest::Approx(2.5)); // std::stod ignores trailing garbage
  CHECK(cfg.getDoubleIfExist("d2", d));
  CHECK(d == doctest::Approx(42.0)); // integer text converts to double

  unsigned u = 0;
  CHECK(cfg.getUnsignedIfExist("u1", u));
  CHECK(u == 3u); // std::stol truncation
  CHECK(cfg.getUnsignedIfExist("u2", u));
  CHECK(u == 4294967291u); // negative int text wraps in the unsigned target

  bool b = false;
  CHECK(cfg.getBoolIfExist("b1", b));
  CHECK(b == true);  // numeric fallback: non-zero means true
  CHECK(cfg.getBoolIfExist("b3", b));
  CHECK(b == true);
  // "on" is not a recognised boolean and not parseable as a number either
  REQUIRE_THROWS_AS(cfg.getBoolIfExist("b2", b), Prompt::Error::BadInput);
}

TEST_CASE("CfgParser vector values tolerate whitespace around components")
{
  auto cfg = parseCfg("v = 1 , 2 , 3");
  pt::Vector v;
  CHECK(cfg.getVectorIfExist("v", v));
  CHECK(v.x() == doctest::Approx(1.0));
  CHECK(v.y() == doctest::Approx(2.0));
  CHECK(v.z() == doctest::Approx(3.0));

  auto neg = parseCfg("v=-1,-2,-3");
  CHECK(neg.getVectorIfExist("v", v));
  CHECK(v.x() == doctest::Approx(-1.0));
  CHECK(v.y() == doctest::Approx(-2.0));
  CHECK(v.z() == doctest::Approx(-3.0));
}

TEST_CASE("CfgParser long cfg strings: many sections and very long values")
{
  std::string big;
  for (int i = 0; i < 500; ++i) {
    if (i)
      big += ";";
    big += "k" + std::to_string(i) + "=v" + std::to_string(i);
  }
  auto cfg = parseCfg(big);
  CHECK(cfg.size() == 500);
  CHECK(cfg.name == "k0=v0");
  CHECK(cfg.find("k0") == "v0");
  CHECK(cfg.find("k250") == "v250");
  CHECK(cfg.find("k499") == "v499");
  CHECK_FALSE(cfg.contains("k500"));

  std::string longval(10000, 'x');
  longval.front() = 'A';
  longval.back() = 'Z';
  auto wide = parseCfg("key=" + longval + ";j=k");
  CHECK(wide.size() == 2);
  CHECK(wide.find("key").size() == 10000);
  CHECK(wide.find("key").front() == 'A');
  CHECK(wide.find("key").back() == 'Z');
  CHECK(wide.find("j") == "k");
}

TEST_CASE("CfgParser round trip: map-ordered reconstruction re-parses identically")
{
  auto cfg = parseCfg("b=2;a=1;c=3;d=0.5;e=1,2,3");
  CHECK(cfg.size() == 5);

  // parameters is a std::map, so iteration order is sorted by key
  std::string rt;
  bool first = true;
  for (auto it = cfg.parameters.begin(); it != cfg.parameters.end(); ++it) {
    if (!first)
      rt += ";";
    first = false;
    rt += it->first + "=" + it->second;
  }
  CHECK(rt == "a=1;b=2;c=3;d=0.5;e=1,2,3");

  auto reparsed = parseCfg(rt);
  CHECK(reparsed.size() == cfg.size());
  CHECK(reparsed.name == "a=1");
  CHECK(reparsed.find("a") == "1");
  CHECK(reparsed.find("b") == "2");
  CHECK(reparsed.find("c") == "3");

  double d = 0.;
  CHECK(reparsed.getDoubleIfExist("d", d));
  CHECK(d == doctest::Approx(0.5));

  pt::Vector v;
  CHECK(reparsed.getVectorIfExist("e", v));
  CHECK(v.x() == doctest::Approx(1.0));
  CHECK(v.y() == doctest::Approx(2.0));
  CHECK(v.z() == doctest::Approx(3.0));
}
