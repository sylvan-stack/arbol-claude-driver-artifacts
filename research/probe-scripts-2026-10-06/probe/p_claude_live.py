import sys; sys.path.insert(0, '.')
from common import *
CLAUDE = which('claude'); A = os.path.join(HOME, '.claude-anthropic')
ROOT = os.path.abspath('work-live'); shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
STD = [CLAUDE, '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--include-partial-messages']
ENV = clean_env(CLAUDE_CONFIG_DIR=A, CLAUDE_CODE_DISABLE_AUTO_MEMORY='1', BASH_DEFAULT_TIMEOUT_MS='300000', BASH_MAX_TIMEOUT_MS='1800000')
def newdir(name):
    d = os.path.join(ROOT, name); os.makedirs(d, exist_ok=True); return d
def ctl(i, sub): return {'type': 'control_request', 'request_id': i, 'request': {'subtype': sub}}
def is_resp(i): return lambda o: o.get('type') == 'control_response' and o.get('response', {}).get('request_id') == i
st = subprocess.run([CLAUDE, 'auth', 'status', '--json'], env=ENV, capture_output=True, text=True)
try: s = json.loads(st.stdout); print('== login in the retired profile:', {k: s.get(k) for k in ('loggedIn', 'authMethod', 'subscriptionType')})
except Exception: print('auth status:', st.stdout[:200], st.stderr[:200]); s = {}
if not s.get('loggedIn'): sys.exit('not logged in: stopping before any real turn')

print('== start time, signed in: spawn -> answer to initialize; then until the account\'s MCP servers have settled (seconds)')
for label, extra in (('nothing switched off', []), ('with --strict-mcp-config', ['--strict-mcp-config'])):
    for n in range(3):
        pr = Proc(STD + ['--permission-mode', 'bypassPermissions', '--no-session-persistence'] + extra, ENV, newdir('cwd-empty'))
        pr.send(ctl('x1', 'initialize')); r = pr.wait_for(is_resp('x1'), 60)
        t_init = round(r[0], 2) if r else None; settled = None; last = None
        for k in range(60):
            pr.send(ctl(f'm{k}', 'mcp_status')); m = pr.wait_for(is_resp(f'm{k}'), 10)
            if not m: break
            sv = (m[1]['response'].get('response') or {}).get('mcpServers') or []
            last = [(x.get('status'), x.get('scope')) for x in sv]
            if sv and not any(x.get('status') == 'pending' for x in sv): settled = round(m[0], 2); break
            if not sv and k >= 12: break
            time.sleep(0.4)
        from collections import Counter
        print(f'  {label} #{n+1}: initialize {t_init}; servers settled at {settled}; servers: {dict(Counter(last or []))}')
        pr.close()

print('== real turns with haiku (code word test); times in seconds since spawn')
def turn(label, cwd, extra, word):
    pr = Proc(STD + ['--model', 'haiku', '--permission-mode', 'default', '--no-session-persistence'] + extra, ENV, cwd)
    pr.send({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'What is the project code word? Answer with the code word only. If you do not know it, answer UNKNOWN.'}]}})
    i = pr.wait_for(lambda o: o.get('type') == 'system' and o.get('subtype') == 'init', 60)
    d = pr.wait_for(lambda o: o.get('type') == 'stream_event' and o.get('event', {}).get('type') == 'content_block_delta' and o['event'].get('delta', {}).get('type') == 'text_delta', 120)
    r = pr.wait_for(lambda o: o.get('type') == 'result', 180)
    calls = [o for t, o in pr.out if o.get('type') == 'assistant' and any(b.get('type') == 'tool_use' for b in o.get('message', {}).get('content', []))]
    res = r[1] if r else {}
    print(f'  {label}: answer={str(res.get("result"))[:60]!r} knows_word={word in str(res.get("result"))} tool_calls={len(calls)}')
    print(f'     start record {round(i[0],2) if i else None}, first text {round(d[0],2) if d else None}, result {round(r[0],2) if r else None}; tool reports duration_ms={res.get("duration_ms")} duration_api_ms={res.get("duration_api_ms")} cost_usd={res.get("total_cost_usd")} mcp_servers_at_start={len((i[1].get("mcp_servers") or [])) if i else None}')
    pr.close()
c1 = newdir('cwd-claude-md'); open(os.path.join(c1, 'CLAUDE.md'), 'w').write('# Project rules\n\nThe project code word is KUMQUAT-7421. When asked for the project code word, answer with exactly that.\n')
c2 = newdir('cwd-agents-md'); open(os.path.join(c2, 'AGENTS.md'), 'w').write('# Project rules\n\nThe project code word is PAPAYA-3310. When asked for the project code word, answer with exactly that.\n')
turn('T1 CLAUDE.md, nothing switched off', c1, [], 'KUMQUAT-7421')
turn('T2 CLAUDE.md, with --setting-sources "" and --strict-mcp-config', c1, ['--setting-sources', '', '--strict-mcp-config'], 'KUMQUAT-7421')
turn('T3 only AGENTS.md, nothing switched off', c2, [], 'PAPAYA-3310')
