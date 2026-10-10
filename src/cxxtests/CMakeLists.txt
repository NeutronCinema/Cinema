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
