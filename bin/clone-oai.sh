#!/bin/bash
# This and other scripts originally taken from https://gitlab.flux.utah.edu/powder-profiles/oai-5g-e2e-rfsim.

source /local/repository/bin/typer.sh
typer "git clone --branch 2021.w46-powder --depth 1 \
https://gitlab.flux.utah.edu/powder-mirror/openairinterface5g /z/openairinterface5g"
