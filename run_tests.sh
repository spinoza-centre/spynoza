#!/usr/bin/env bash
py.test -v --cov spynoza --cov-report term-missing spynoza -m "not confound"
