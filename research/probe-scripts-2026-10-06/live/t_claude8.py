import sys, json, signal
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("def shape")[0])
def alive(pattern):
    r = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True); return [int(x) for x in r.stdout.split()]
print('=== D5: end what the shell calls left behind, by the process group of each noted shell call')
cwd = os.path.join(ROOT, 'bg5'); os.makedirs(cwd); wdir = os.path.join(ROOT, 'bg5-shell'); os.makedirs(wdir)
wrapper = os.path.join(wdir, 'zsh'); notes = os.path.join(wdir, 'calls')
open(wrapper, 'w').write(f'#!/bin/sh\necho $$ >> "{notes}"\nexec /bin/zsh "$@"\n'); os.chmod(wrapper, 0o700)
env = dict(ENV); env['CLAUDE_CODE_SHELL'] = wrapper
pr = Proc(STD, env, cwd)
pr.send(user("Run exactly this with your Bash tool as an ordinary call: `nohup sleep 73 >/dev/null 2>&1 & echo launched; echo shell=$SHELL`. Then reply with the single word STARTED."))
r = pr.wait_for(lambda o: o.get('type') == 'result', 120); time.sleep(0.5)
tr = [str(b.get('content'))[:90] for t, o in pr.out if o.get('type') == 'user' for b in (o.get('message', {}).get('content') if isinstance(o.get('message', {}).get('content'), list) else []) if b.get('type') == 'tool_result']
print('  tool result:', tr)
try: pr.p.stdin.close()
except Exception: pass
try: pr.p.wait(40)
except Exception: pass
print('  claude exit:', pr.p.returncode)
noted = [int(x) for x in open(notes).read().split()]
left = alive('sleep 73')
print('  noted shell calls:', len(noted), '| left after the exit:', [(p, 'session', os.getsid(p), 'group', os.getpgid(p), 'group is a noted call:', os.getpgid(p) in noted) for p in left])
sent = 0
for n in noted:
    try: os.killpg(n, signal.SIGTERM); sent += 1
    except ProcessLookupError: pass
time.sleep(0.5); print('  groups that still had a process:', sent, '| left after ending them:', alive('sleep 73'))
for p in alive('sleep 73'): os.kill(p, 9)
