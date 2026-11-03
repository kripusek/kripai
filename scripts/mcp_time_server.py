"""Uruchomienie jednego przypiętego dostawcy w osobnym procesie i zależnościach."""
import sys,site
from pathlib import Path

if len(sys.argv)!=2:raise SystemExit(2)
folder=Path(sys.argv[1]);deps=folder/'deps'
if not folder.is_absolute() or folder.name!='mcp-time-2026.10.28-py313' or not deps.is_dir():raise SystemExit(2)
sys.path.insert(0,str(deps))
# Obsługa przypiętych rozszerzeń Windows (pywin32), wyłącznie w tym procesie.
site.addsitedir(str(deps))
sys.argv=['mcp-server-time','--local-timezone','Europe/Warsaw']
from mcp_server_time import main
main()
