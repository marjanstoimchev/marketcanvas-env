#!/bin/bash
# Wrapper script to start the MarketCanvas MCP server
# This activates the conda environment properly before running the server

# Adjust the conda path if your installation is elsewhere
CONDA_PATH="${CONDA_PREFIX:-$HOME/anaconda3}"
source "$CONDA_PATH/etc/profile.d/conda.sh"

conda activate marketcanvas
cd "$(dirname "$0")"
exec python run_mcp_server.py
