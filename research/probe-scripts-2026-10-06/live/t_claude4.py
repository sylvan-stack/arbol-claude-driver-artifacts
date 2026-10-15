import sys, json, uuid, signal, glob
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("print('=== T1a")[0])
def alive(pattern):
    r = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True); return [int(x) for x in r.stdout.split()]
BASE = [a for a in STD if a != '--no-session-persistence']
def one(cwd, extra, text):
    pr = Proc(BASE + extra, ENV, cwd); pr.send(user(text)); r = pr.wait_for(lambda o: o.get('type') == 'result', 120); pr.close(); return (str(r[1].get('result'))[:60] if r else None)
print('=== C2: a changed system prompt on a continued conversation; the first run never mentions the word')
ASK = 'Does your system prompt name a project code word? Reply with the code word only, or NONE.'
for label, flags in (('default', []), ('with --no-system-prompt-snapshot', ['--no-system-prompt-snapshot'])):
    cwd = os.path.join(ROOT, 'sp-' + label[:4]); os.makedirs(cwd); sid = str(uuid.uuid4())
    a = one(cwd, ['--session-id', sid, '--append-system-prompt', 'The project code word is ALPHA-1.'] + flags, 'Reply with the single word READY.')
    b = one(cwd, ['--resume', sid, '--append-system-prompt', 'The project code word is BETA-2.'] + flags, ASK)
    c = one(cwd, ['--resume', sid] + flags, ASK)
    print(f'  {label}: first run -> {a!r}; continued with BETA-2 -> {b!r}; continued with no prompt -> {c!r}')
    for f in glob.glob(os.path.join(H, 'projects', '*', sid + '*')):
        (shutil.rmtree if os.path.isdir(f) else os.remove)(f)
print('=== D2: a command that detaches itself inside an ordinary shell call')
cwd = os.path.join(ROOT, 'bg2'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd); leader = pr.p.pid; sess = os.getsid(leader)
pr.send(user("Run exactly this with your Bash tool, as an ordinary call and not with run_in_background: `nohup sleep 59 >/dev/null 2>&1 & echo launched`. Then reply with the single word STARTED."))
r = pr.wait_for(lambda o: o.get('type') == 'result', 120); time.sleep(1)
def info(pids):
    out = []
    for p in pids:
        try: out.append({'pid': p, 'in_claudes_session': os.getsid(p) == sess, 'own_group': os.getpgid(p) == p, 'parent': int(subprocess.run(['ps', '-o', 'ppid=', '-p', str(p)], capture_output=True, text=True).stdout or 0), 'descends_from_claude': None})
        except Exception as e: out.append({'pid': p, 'error': str(e)})
    return out
during = info(alive('sleep 59')); print('  while claude runs:', during, '| claude pid', leader, '| answer:', (str(r[1].get('result'))[:30] if r else None))
try: pr.p.stdin.close()
except Exception: pass
try: rc = pr.p.wait(40)
except Exception: rc = 'still running after 40 s'
time.sleep(1); after = alive('sleep 59'); print('  claude exit:', rc, '| still alive afterwards:', info(after))
for p in after:
    try: os.kill(p, signal.SIGKILL)
    except Exception: pass
print('  cleaned up:', len(alive('sleep 59')) == 0)
