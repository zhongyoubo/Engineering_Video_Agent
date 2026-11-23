"""Routine source checks; integration media tests are intentionally opt-in."""
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
os.chdir(root)
commands=[
    [sys.executable,'-m','ruff','check','apps/api/src','apps/api/tests'],
    [sys.executable,'-m','pytest','apps/api/tests','-q'],
    ['npm.cmd' if os.name=='nt' else 'npm','run','test:visual'],
    ['node','scripts/verify_spatial_contracts.cjs'],
    ['node','scripts/verify_creative_contracts.cjs'],
    ['npm.cmd' if os.name=='nt' else 'npm','run','typecheck'],
    ['npm.cmd' if os.name=='nt' else 'npm','run','build'],
]
for command in commands:
    subprocess.run(command,check=True)

