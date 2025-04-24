#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
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

import os
from functools import wraps
import importlib.util

def has_package_in_env(package_name):
    return importlib.util.find_spec(package_name) is not None

def findData(fn, dir='data'):
    fs=fn.split('/')
    if len(fs)!=2:
        raise RuntimeError('findData input should be something like Al/cell.json')
    pxpath = os.getenv('CINEMAPATH')+ f'/{dir}/' + fs[0]+'/'
    # print(pxpath)
    fnlist=[]
    for root, dirs, files in os.walk(pxpath):
        if fs[1] in files:
            fnlist.append(os.path.join(root, fs[1]))
    if len(fnlist)!=1:
        raise RuntimeError(f'{len(fnlist)} {fn} files found')
    return fnlist[0]

#example findData('Al/cell.json')