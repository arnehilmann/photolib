#!/bin/bash

VE_DIR=ve

echo "checking install path"
if [[ ! -d bootstrap ]]; then
    echo "must be called in project dir, as 'bootstrap/ubuntu.sh'!"
    exit 2
fi

echo "checking environment"
virtualenv --version > /dev/null 2>&1 || sudo apt-get install python-virtualenv
jhead -V > /dev/null 2>&1 || sudo apt-get install jhead

echo "preparing virtualenv in '$VE_DIR'"
rm -rf $VE_DIR
virtualenv $VE_DIR
. $VE_DIR/bin/activate
pip install pybuilder Wand docopt
ln -sf $PWD/src/main/scripts/* $PWD/$VE_DIR/bin
ln -sf $PWD/src/main/python/* $PWD/$VE_DIR/lib/python*/site-packages

echo "remember to 'source $VE_DIR/bin/activate' as first step."
