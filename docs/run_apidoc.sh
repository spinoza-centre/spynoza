#!/usr/bin/env bash

root="$(dirname `pwd`)"/spynoza

rm source/*.rst
sphinx-apidoc -o source -fMeT $root $root/*/tests $root/*/*/tests $root/*/*/*/tests $root/data
