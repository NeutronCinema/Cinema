#!/bin/bash

cd docs/
rm -rf build
rm -rf source/_doxygen
rm -rf source/api

make html
cd ../