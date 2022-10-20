#!/bin/bash

if { conda env list | grep 'cinema_doc'; } >/dev/null 2>&1
then conda activate cinema_doc
else conda env create -f environmentDoc.yml && conda activate cinema_doc
fi

cd docs/
rm -rf build
rm -rf source/_doxygen
rm -rf source/api

make html
cd ..