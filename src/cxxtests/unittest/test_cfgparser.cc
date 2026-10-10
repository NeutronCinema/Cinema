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

#include "../doctest.h"

#include "PTCfgParser.hh"
#include "PTSingleton.hh"
#include "PTUtils.hh"
#include "PTVector.hh"

#include <string>
#include <typeinfo>

namespace pt = Prompt;

// Helper: parse through the CfgParser singleton (private constructor).
static pt::CfgParser::StringCfg parseCfg(const std::string& str)
{
  return pt::Singleton<pt::CfgParser>::getInstance().parse(str);
}

TEST_CASE("CfgParser basic sections: find, contains and size")
{
  auto cfg = parseCfg("k1=v1;k2=v2");
  CHECK(cfg.size() == 2);
  CHECK(cfg.find("k1") == "v1");
  CHECK(cfg.find("k2") == "v2");
  CHECK(cfg.contains("k1"));
  CHECK(cfg.contains("k2"));
  CHECK_FALSE(cfg.contains("k3"));
  // the cfg name is the entire first section (see also the single-section case)
  CHECK(cfg.name == "k1=v1");
}

TEST_CASE("CfgParser strips whitespace around '=' and ';' and within values")
{
  auto cfg = parseCfg("k1 = v1 ; k2 =\tv2\t");
  CHECK(cfg.size() == 2);
  CHECK(cfg.find("k1") == "v1");
  CHECK(cfg.find("k2") == "v2");

  // split() removes *all* whitespace inside a token, so unquoted values
  // with internal spaces are concatenated - pin this documented behaviour
  auto cfg2 = parseCfg("p= a b ");
  CHECK(cfg2.find("p") == "ab");
}

TEST_CASE("CfgParser quoted value survives ';' and '=' and keeps spaces")
{
  // a single quoted section per cfg string is fully supported: the quoted
  // substring is parked in a magic-substring placeholder during splitting
  auto cfg = parseCfg("cfg='a;b=c'");
  CHECK(cfg.size() == 1);
  CHECK(cfg.contains("cfg"));
  CHECK(cfg.find("cfg") == "a;b=c");

  // quoted values keep internal whitespace (unlike unquoted ones)
  auto cfg2 = parseCfg("note='hello world';k=v");
  CHECK(cfg2.size() == 2);
  CHECK(cfg2.find("note") == "hello world");
  CHECK(cfg2.find("k") == "v");
}

TEST_CASE("CfgParser odd number of quotes throws BadInput")
{
  REQUIRE_THROWS_AS(parseCfg("a='x"), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(parseCfg("'"), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(parseCfg("a='x;b='y'"), Prompt::Error::BadInput);
  // an even number of quotes parses fine
  CHECK_NOTHROW(parseCfg("a='x'"));
}

TEST_CASE("CfgParser StringCfg::find: missing key returns empty, force throws")
{
  auto cfg = parseCfg("k=v");
  CHECK(cfg.find("missing").empty());
  CHECK_FALSE(cfg.contains("missing"));
  REQUIRE_THROWS_AS(cfg.find("missing", true), Prompt::Error::BadInput);
  // force=true on an existing key does not throw
  CHECK_NOTHROW(cfg.find("k", true));
}

TEST_CASE("CfgParser typed getters: double, int, unsigned, vector")
{
  auto cfg = parseCfg("d=293.15;sci=1e-3;i=-42;u=42;v=0,0,-1400");

  double d = 0.;
  CHECK(cfg.getDoubleIfExist("d", d));
  CHECK(d == doctest::Approx(293.15));
  CHECK(cfg.getDoubleIfExist("sci", d));
  CHECK(d == doctest::Approx(0.001));

  int i = 0;
  CHECK(cfg.getIntIfExist("i", i));
  CHECK(i == -42);

  unsigned u = 0;
  CHECK(cfg.getUnsignedIfExist("u", u));
  CHECK(u == 42u);

  pt::Vector v;
  CHECK(cfg.getVectorIfExist("v", v));
  CHECK(v.x() == doctest::Approx(0.0));
  CHECK(v.y() == doctest::Approx(0.0));
  CHECK(v.z() == doctest::Approx(-1400.0));

  // missing keys report false and leave the output argument untouched
  double dref = 3.14;
  CHECK_FALSE(cfg.getDoubleIfExist("nope", dref));
  CHECK(dref == doctest::Approx(3.14));

  // malformed values propagate the conversion BadInput error
  auto bad = parseCfg("s=abc");
  double tmp = 0.;
  int itmp = 0;
  unsigned utmp = 0;
  pt::Vector vtmp;
  REQUIRE_THROWS_AS(bad.getDoubleIfExist("s", tmp), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(bad.getIntIfExist("s", itmp), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(bad.getUnsignedIfExist("s", utmp), Prompt::Error::BadInput);

  // a vector value needs exactly three components
  auto short_vec = parseCfg("w=1,2");
  REQUIRE_THROWS_AS(short_vec.getVectorIfExist("w", vtmp), Prompt::Error::BadInput);
}

TEST_CASE("CfgParser getBoolIfExist: true/1/yes, false/0/no and numeric fallback")
{
  auto cfg = parseCfg("b1=TRUE;b2=True;b3=1;b4=yes;b5=YES");
  bool b = false;
  const char* true_keys[] = {"b1", "b2", "b3", "b4", "b5"};
  for (auto key : true_keys) {
    CHECK(cfg.getBoolIfExist(key, b));
    CHECK_MESSAGE(b == true, "key " << key << " must parse as true");
  }

  auto cfgf = parseCfg("c1=False;c2=0;c3=NO;c4=no;c5=FALSE");
  const char* false_keys[] = {"c1", "c2", "c3", "c4", "c5"};
  for (auto key : false_keys) {
    CHECK(cfgf.getBoolIfExist(key, b));
    CHECK_MESSAGE(b == false, "key " << key << " must parse as false");
  }

  // unrecognized strings fall back to ptstod: non-zero means true
  auto num = parseCfg("n1=2.5;n2=0.0");
  CHECK(num.getBoolIfExist("n1", b));
  CHECK(b == true);
  CHECK(num.getBoolIfExist("n2", b));
  CHECK(b == false);

  // absent key returns false without touching the argument
  b = true;
  CHECK_FALSE(cfg.getBoolIfExist("missing", b));
  CHECK(b == true);
}

TEST_CASE("CfgParser rejects sections without '=' and empty values")
{
  // a non-empty section without '=' throws with the documented message
  bool caught = false;
  try {
    parseCfg("a=b;illdefined");
  } catch (const Prompt::Error::BadInput& e) {
    caught = true;
    CHECK(std::string(e.what()).find("ill-defined") != std::string::npos);
    CHECK(std::string(e.what()).find("illdefined") != std::string::npos);
  }
  CHECK(caught);

  REQUIRE_THROWS_AS(parseCfg("illdefined"), Prompt::Error::BadInput);
  // an empty value is dropped by split(), so the section is ill-defined too
  REQUIRE_THROWS_AS(parseCfg("k=;j=v"), Prompt::Error::BadInput);

  // a trailing ';' yields an empty final token which split() drops: tolerated
  auto trailing = parseCfg("a=b;");
  CHECK(trailing.size() == 1);
  CHECK(trailing.find("a") == "b");
}

TEST_CASE("CfgParser empty cfg strings throw BadInput instead of crashing")
{
  // split() drops empty tokens, so an all-empty cfg used to index past the
  // end of the token vector (segfault); it must throw BadInput instead
  CHECK_THROWS_AS(parseCfg(""), Prompt::Error::BadInput);
  CHECK_THROWS_AS(parseCfg(";"), Prompt::Error::BadInput);
  CHECK_THROWS_AS(parseCfg(" ;; "), Prompt::Error::BadInput);
  CHECK_THROWS_AS(parseCfg("   "), Prompt::Error::BadInput);

  // valid strings still parse identically (single- and multi-section)
  auto single = parseCfg("k=v");
  CHECK(single.size() == 1);
  CHECK(single.name == "k=v");
  CHECK(single.find("k") == "v");

  auto multi = parseCfg("a=b;c=d");
  CHECK(multi.size() == 2);
  CHECK(multi.name == "a=b");
  CHECK(multi.find("a") == "b");
  CHECK(multi.find("c") == "d");
}

TEST_CASE("CfgParser single-section string: name is the whole first section")
{
  auto cfg = parseCfg("k=v");
  CHECK(cfg.size() == 1);
  CHECK(cfg.name == "k=v");
  CHECK(cfg.find("k") == "v");
}

TEST_CASE("CfgParser regression anchor: production Scorer cfg string")
{
  // the exact string used by ScorerFactory / test_cfgpaser.cc
  auto cfg = parseCfg("Scorer=DeltaMomentum; name=SofQ;sample_pos=0,0,1;"
                      "beam_dir=0,0,1;dist=30000;ScorerType=ENTRY;linear=true");
  CHECK(cfg.size() == 7);
  CHECK(cfg.name == "Scorer=DeltaMomentum");
  CHECK(cfg.find("Scorer") == "DeltaMomentum");
  CHECK(cfg.find("name") == "SofQ");
  CHECK(cfg.find("ScorerType") == "ENTRY");

  pt::Vector pos, dir;
  CHECK(cfg.getVectorIfExist("sample_pos", pos));
  CHECK(pos.x() == doctest::Approx(0.0));
  CHECK(pos.y() == doctest::Approx(0.0));
  CHECK(pos.z() == doctest::Approx(1.0));
  CHECK(cfg.getVectorIfExist("beam_dir", dir));
  CHECK(dir.x() == doctest::Approx(0.0));
  CHECK(dir.y() == doctest::Approx(0.0));
  CHECK(dir.z() == doctest::Approx(1.0));

  double dist = 0.;
  CHECK(cfg.getDoubleIfExist("dist", dist));
  CHECK(dist == doctest::Approx(30000.0));

  bool linear = false;
  CHECK(cfg.getBoolIfExist("linear", linear));
  CHECK(linear == true);
}

TEST_CASE("CfgParser StringCfg::getStringIfExist reports presence")
{
  auto cfg = parseCfg("name=SofQ");
  std::string str = "untouched";
  CHECK(cfg.getStringIfExist("name", str));
  CHECK(str == "SofQ");
  // absent key: returns false, leaves the argument unmodified
  CHECK_FALSE(cfg.getStringIfExist("missing", str));
  CHECK(str == "SofQ");
}

TEST_CASE("CfgParser getDoubleIfExist parses decimal and scientific notation")
{
  auto cfg = parseCfg("t=293.15;s=1e-3;n=-2.5e2");
  double v = 0.;
  CHECK(cfg.getDoubleIfExist("t", v));
  CHECK(v == doctest::Approx(293.15));
  CHECK(cfg.getDoubleIfExist("s", v));
  CHECK(v == doctest::Approx(1e-3));
  CHECK(cfg.getDoubleIfExist("n", v));
  CHECK(v == doctest::Approx(-250.0));
}

TEST_CASE("ptUtils string2vec parses comma-separated 3-vectors")
{
  auto v = pt::string2vec("0,0,-1400");
  CHECK(v.x() == doctest::Approx(0.0));
  CHECK(v.y() == doctest::Approx(0.0));
  CHECK(v.z() == doctest::Approx(-1400.0));

  auto w = pt::string2vec("1.5,-2.25,3e1");
  CHECK(w.x() == doctest::Approx(1.5));
  CHECK(w.y() == doctest::Approx(-2.25));
  CHECK(w.z() == doctest::Approx(30.0));

  // anything other than exactly three components throws
  REQUIRE_THROWS_AS(pt::string2vec("1,2"), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::string2vec("1,2,3,4"), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::string2vec(""), Prompt::Error::BadInput);
}

TEST_CASE("ptUtils string2vec accepts a custom delimiter")
{
  auto v = pt::string2vec("1;2;3", ';');
  CHECK(v.x() == doctest::Approx(1.0));
  CHECK(v.y() == doctest::Approx(2.0));
  CHECK(v.z() == doctest::Approx(3.0));

  // delimiting whitespace is stripped by split()
  auto w = pt::string2vec(" 1 ; 2 ; 3 ", ';');
  CHECK(w.x() == doctest::Approx(1.0));
  CHECK(w.y() == doctest::Approx(2.0));
  CHECK(w.z() == doctest::Approx(3.0));
}

TEST_CASE("ptUtils ptstod parses doubles, accepts prefixes and rejects garbage")
{
  CHECK(pt::ptstod("2.5e2") == doctest::Approx(250.0));
  CHECK(pt::ptstod("-0.125") == doctest::Approx(-0.125));
  CHECK(pt::ptstod("1e-3") == doctest::Approx(1e-3));
  // std::stod prefix-parse: trailing garbage after a valid number is ignored
  CHECK(pt::ptstod("3.5abc") == doctest::Approx(3.5));
  // pure garbage throws BadInput
  REQUIRE_THROWS_AS(pt::ptstod("garbage"), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::ptstod(""), Prompt::Error::BadInput);
}

TEST_CASE("CfgParser repeated keys: last assignment wins")
{
  auto cfg = parseCfg("k=1;k=2");
  CHECK(cfg.size() == 1);
  CHECK(cfg.find("k") == "2");

  auto cfg2 = parseCfg("a=1;b=2;a=3");
  CHECK(cfg2.size() == 2);
  CHECK(cfg2.find("a") == "3");
  CHECK(cfg2.find("b") == "2");
}
