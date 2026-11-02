"""Stałe lokalnej instalacji. Żaden adres ani program nie pochodzi z czatu."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCAL=Path(os.getenv('LOCALAPPDATA',str(Path.home()/'.local/share')))
DATA=Path(os.getenv('KRIPAI_DATA',str(LOCAL/'KripAI-data')))
BACKUPS=Path(os.getenv('KRIPAI_BACKUPS',str(LOCAL/'KripAI-backups')))
PORT=8765
ORIGIN=f'http://localhost:{PORT}'
LLM='http://127.0.0.1:8766'
CONTEXT=4096
OUTPUT=2048

def llm_headers():
    return {'Authorization':'Bearer '+(DATA/'llm.key').read_text().strip()}
