#!/bin/sh
PYTHONIOENCODING=UTF-8
export PYTHONIOENCODING
LANG=es_ES.UTF-8
export LANG

$(dirname $0)/con_puente.py > $(dirname $0)/tren.log 2>&1
