import sys, json, signal
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("print('=== T1a")[0])
def alive(pattern):
    r = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True); return [int(x) for x in r.stdout.split()]
print('=== D4: a shell of the Driver\'s own that notes the session of every shell call')
cwd = os.path.join(ROOT, 'bg4'); os.makedirs(cwd); wdir = os.path.join(ROOT, 'bg4-shell'); os.makedirs(wdir)
wrapper = os.path.join(wdir, 'zsh'); notes = os.path.join(wdir, 'sessions')
open(wrapper, 'w').write(f'#!/bin/sh\necho $$ >> "{notes}"\nexec /bin/zsh "$@"\n'); os.chmod(wrapper, 0o700)
for label, extra_env in (('CLAUDE_CODE_SHELL', {'CLAUDE_CODE_SHELL': wrapper}), ('SHELL', {'SHELL': wrapper})):
    if os.path.exists(notes): os.remove(notes)
    env = dict(ENV); env.update(extra_env)
    pr = Proc(STD, env, cwd)
    n = 71 if label == 'SHELL' else 70
    pr.send(user(f"Run exactly this with your Bash tool as an ordinary call: `nohup sleep {n} >/dev/null 2>&1 & echo launched`. Then reply with the single word STARTED."))
    r = pr.wait_for(lambda o: o.get('type') == 'result', 120); time.sleep(0.5)
    init = next((o for t, o in pr.out if o.get('type') == 'system' and o.get('subtype') == 'init'), {})
    noted = [int(x) for x in open(notes).read().split()] if os.path.exists(notes) else []
    left = alive(f'sleep {n}'); sids = []
    for p in left:
        try: sids.append(os.getsid(p))
        except Exception: sids.append(None)
    tr = [str(b.get('content'))[:60] for t, o in pr.out if o.get('type') == 'user' for b in (o.get('message', {}).get('content') if isinstance(o.get('message', {}).get('content'), list) else []) if b.get('type') == 'tool_result']
    print(f'  with {label}: answer={str(r[1].get("result"))[:20] if r else None!r}; tool results={tr}; wrapper ran {len(noted)} times; leftover sessions {sids}; each is among the noted ones: {[s in noted for s in sids]}')
    try: pr.p.stdin.close()
    except Exception: pass
    try: pr.p.wait(40)
    except Exception: pass
    for p in alive(f'sleep {n}'):
        try: os.kill(p, signal.SIGKILL)
        except Exception: pass
