################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################


project(prompt_test)

add_library(test_main OBJECT test_main.cpp)

file(GLOB TESTFILES "${PROJECT_SOURCE_DIR}/unittest/*.cc" "${PROJECT_SOURCE_DIR}/unittest/*.c")
foreach(TS ${TESTFILES})
  get_filename_component(EXCNAME  ${TS}  NAME_WE)
  add_executable( ${EXCNAME} ${TS} $<TARGET_OBJECTS:test_main>)
  target_link_libraries( ${EXCNAME} pthread prompt_core)
  add_test(NAME ${EXCNAME} COMMAND ${EXCNAME} )
endforeach(TS ${TESTFILES})

# Fake physics-model plugins for test_pluginregistry, built as MODULE
# libraries (dlopen targets) and passed to the test through the environment.
# plugins/ stays out of the test glob above: these are loaded, not executed.
add_library(cinplugin_testhello MODULE unittest/plugins/plugin_test_hello.cc)
target_link_libraries(cinplugin_testhello prompt_core)
target_compile_definitions(cinplugin_testhello PRIVATE CINPLUGIN_NAME=TestHello)
set_target_properties(cinplugin_testhello PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)

add_library(cinplugin_testbadabi MODULE unittest/plugins/plugin_test_badabi.cc)
target_link_libraries(cinplugin_testbadabi prompt_core)
set_target_properties(cinplugin_testbadabi PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)

set_property(TEST test_pluginregistry PROPERTY ENVIRONMENT
  "CINPLUGIN_TEST_HELLO=$<TARGET_FILE:cinplugin_testhello>;CINPLUGIN_TEST_BADABI=$<TARGET_FILE:cinplugin_testbadabi>")
set_property(TEST test_pluginregistry PROPERTY DEPENDS cinplugin_testhello cinplugin_testbadabi)
