"""Downloads each player's current Minecraft skin to frontend/assets/skins/<seed>.png (Players tab 3D easter egg)."""
import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.event import PLAYERS

out = ROOT / 'frontend' / 'assets' / 'skins'
out.mkdir(exist_ok=True)
for seed, uuid, mc_name, *_ in PLAYERS:
    with urllib.request.urlopen(f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}') as r:
        textures = json.loads(base64.b64decode(json.load(r)['properties'][0]['value']))['textures']
    with urllib.request.urlopen(textures['SKIN']['url'].replace('http://', 'https://')) as r:
        (out / f'{seed}.png').write_bytes(r.read())
    print(seed, mc_name)
