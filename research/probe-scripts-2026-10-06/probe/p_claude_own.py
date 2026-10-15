import sys; sys.path.insert(0, '.')
from common import *
CLAUDE = which('claude')
ROOT = os.path.abspath('work-own'); shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
home = os.path.join(ROOT, 'home'); os.makedirs(home); cwd = os.path.join(ROOT, 'cwd'); os.makedirs(cwd)
os.symlink(os.path.join(HOME, '.claude', 'skills'), os.path.join(home, 'skills'))
STD = [CLAUDE, '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', '--permission-mode', 'bypassPermissions', '--no-session-persistence']
def ctl(i, sub): return {'type': 'control_request', 'request_id': i, 'request': {'subtype': sub}}
def is_resp(i): return lambda o: o.get('type') == 'control_response' and o.get('response', {}).get('request_id') == i
pr = Proc(STD + ['--mcp-config', os.path.join(HOME, '.claude.json')], clean_env(CLAUDE_CONFIG_DIR=home, CLAUDE_CODE_DISABLE_AUTO_MEMORY='1'), cwd)
pr.send(ctl('x1', 'initialize')); r = pr.wait_for(is_resp('x1'), 60)
cmds = (r[1]['response'].get('response') or {}).get('commands') or [] if r else []
user = [c['name'] for c in cmds if '(user)' in (c.get('description') or '')]
print(f'initialize after {round(r[0],2) if r else None} s; commands {len(cmds)}, of them from the linked skills folder: {len(user)}; first five: {user[:5]}')
last = None
for k in range(40):
    pr.send(ctl(f'm{k}', 'mcp_status')); m = pr.wait_for(is_resp(f'm{k}'), 10)
    if not m: break
    sv = (m[1]['response'].get('response') or {}).get('mcpServers') or []
    last = [(x.get('name'), x.get('status'), x.get('scope')) for x in sv]
    if sv and not any(x.get('status') == 'pending' for x in sv): print(f'MCP servers settled {round(m[0],2)} s after spawn'); break
    time.sleep(0.5)
print('MCP servers:', last)
pr.close()
