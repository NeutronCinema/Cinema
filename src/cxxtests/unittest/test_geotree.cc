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

#include "PTGeoTree.hh"

namespace pt = Prompt;

TEST_CASE("test_geotree")
{
  auto tree = pt::Singleton<Prompt::GeoTree>::getInstance();
  auto root = tree.getRoot();
  root->physical = 8;
  root->logical = 108;
  auto child1 = std::shared_ptr<pt::GeoTree::Node>(new pt::GeoTree::Node {7,107});
  auto child2 = std::shared_ptr<pt::GeoTree::Node>(new pt::GeoTree::Node {6,106});

  root->addChild(child1);
  root->addChild(child2);
  auto child1_child1 = std::shared_ptr<pt::GeoTree::Node>(new pt::GeoTree::Node {5,105});
  auto child1_child2 = std::shared_ptr<pt::GeoTree::Node>(new pt::GeoTree::Node {4,105});

  child1->addChild(child1_child1);
  child1->addChild(child1_child2);

  tree.print();
}
