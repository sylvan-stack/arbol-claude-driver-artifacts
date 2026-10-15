import sys; sys.path.insert(0, '.')
from common import *
CLAUDE = which('claude')
ROOT = os.path.abspath('work'); shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
STD = [CLAUDE, '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--include-partial-messages']
DRIVER = ['--permission-mode', 'bypassPermissions']
ENV_EXTRA = {'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'BASH_DEFAULT_TIMEOUT_MS': '300000', 'BASH_MAX_TIMEOUT_MS': '1800000'}
def newdir(name):
    d = os.path.join(ROOT, name); os.makedirs(d, exist_ok=True); return d
def init_req(i='x1'): return {'type': 'control_request', 'request_id': i, 'request': {'subtype': 'initialize'}}
def ctl(i, sub): return {'type': 'control_request', 'request_id': i, 'request': {'subtype': sub}}
def is_resp(i): return lambda o: o.get('type') == 'control_response' and o.get('response', {}).get('request_id') == i
def start(home, cwd, extra):
    return Proc(STD + DRIVER + extra, clean_env(CLAUDE_CONFIG_DIR=home, **ENV_EXTRA), cwd)

print('== P1 start time, empty home: spawn -> answer to initialize (seconds)')
for label, extra in (('nothing switched off', []), ('old switches', ['--setting-sources', '', '--strict-mcp-config'])):
    ts = []
    for n in range(4):
        home = newdir(f'home-p1-{label[:3]}-{n}') if n == 0 else home
        pr = start(home, newdir('cwd-empty'), extra); pr.send(init_req())
        r = pr.wait_for(is_resp('x1'), 60); ts.append(round(r[0], 2) if r else None); pr.close()
    print(f'  {label}: first start {ts[0]}, later starts {ts[1:]}')

print('== P2 skills by link, MCP by --mcp-config, in an empty home')
home = newdir('home-p2'); cwd = newdir('cwd-p2')
sk = newdir('owner-skills/probe-skill')
open(os.path.join(sk, 'SKILL.md'), 'w').write('---\nname: probe-skill\ndescription: Probe skill for discovery tests. Use when asked for the probe word.\n---\nThe probe word is BANANA.\n')
os.symlink(os.path.join(ROOT, 'owner-skills'), os.path.join(home, 'skills'))
mcp_plain = os.path.join(ROOT, 'mcp-plain.json'); json.dump({'mcpServers': {'probe-server': {'command': '/usr/bin/true', 'args': []}}}, open(mcp_plain, 'w'))
mcp_extra = os.path.join(ROOT, 'mcp-extra.json'); json.dump({'numStartups': 3, 'projects': {}, 'oauthAccount': {'x': 1}, 'mcpServers': {'probe-server': {'command': '/usr/bin/true', 'args': []}}}, open(mcp_extra, 'w'))
for label, extra in (('no mcp arg', []), ('--mcp-config plain file', ['--mcp-config', mcp_plain]), ('--mcp-config file with other top-level keys', ['--mcp-config', mcp_extra])):
    pr = start(home, cwd, extra); pr.send(init_req())
    r = pr.wait_for(is_resp('x1'), 60)
    if not r: print('  ', label, 'NO ANSWER; stderr:', ''.join(pr.err)[:300]); pr.close(); continue
    resp = r[1]['response'].get('response', {})
    cmds = resp.get('commands') or []
    names = [c.get('name') if isinstance(c, dict) else c for c in cmds]
    hit = [c for c in cmds if 'probe' in json.dumps(c)]
    time.sleep(2.5); pr.send(ctl('m1', 'mcp_status')); m = pr.wait_for(is_resp('m1'), 20)
    servers = (m[1]['response'].get('response') or {}).get('mcpServers') if m else None
    print(f'  {label}: commands={len(names)} probe-skill listed={bool(hit)} {json.dumps(hit)[:200] if hit else ""}')
    print(f'     mcp_status: {json.dumps([{k: s.get(k) for k in ("name", "status", "scope")} for s in (servers or [])])}')
    if label == 'no mcp arg': print('     keys of initialize answer:', sorted(resp.keys())); print('     sample command entry keys:', sorted(cmds[0].keys()) if cmds and isinstance(cmds[0], dict) else cmds[:3])
    rc = pr.close(); 
    if pr.err: print('     stderr:', ''.join(pr.err)[:200].strip())

print('== P3 start record in a folder with CLAUDE.md, empty home (turn fails before inference: not logged in)')
cwd = newdir('cwd-p3'); open(os.path.join(cwd, 'CLAUDE.md'), 'w').write('# Project rules\n\nThe project code word is KUMQUAT-7421. When asked for the project code word, answer with exactly that.\n')
for label, extra in (('nothing switched off', []), ('--setting-sources ""', ['--setting-sources', ''])):
    pr = start(newdir('home-p3-' + label[:3]), cwd, extra + ['--no-session-persistence'])
    pr.send({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'What is the project code word?'}]}})
    r = pr.wait_for(lambda o: o.get('type') == 'system' and o.get('subtype') == 'init', 40)
    res = pr.wait_for(lambda o: o.get('type') == 'result', 40)
    if r:
        init = r[1]
        print(f'  {label}: init keys = {sorted(init.keys())}')
        for k, v in init.items():
            if any(w in k.lower() for w in ('memory', 'claude_md', 'instruction', 'skills', 'plugins', 'agents')): print(f'     {k} = {json.dumps(v)[:300]}')
    print(f'     result: is_error={res[1].get("is_error") if res else None} cost={res[1].get("total_cost_usd") if res else None} text={str(res[1].get("result"))[:80] if res else None}')
    pr.close()
