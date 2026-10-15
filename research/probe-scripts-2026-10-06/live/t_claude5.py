import sys, json, uuid, signal, glob, threading
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("print('=== T1a")[0])
def alive(pattern):
    r = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True); return [int(x) for x in r.stdout.split()]
BASE = [a for a in STD if a != '--no-session-persistence']
def one(cwd, extra, text):
    pr = Proc(BASE + extra, ENV, cwd); pr.send(user(text)); r = pr.wait_for(lambda o: o.get('type') == 'result', 120); rc = pr.close()
    return (str(r[1].get('result'))[:60] if r else ('no result; stderr: ' + ''.join(pr.err)[:160]))
print('=== C3: the same with --system-prompt-snapshot off on every run')
ASK = 'Does your system prompt name a project code word? Reply with the code word only, or NONE.'
cwd = os.path.join(ROOT, 'sp-off'); os.makedirs(cwd); sid = str(uuid.uuid4()); F = ['--system-prompt-snapshot', 'off']
a = one(cwd, ['--session-id', sid, '--append-system-prompt', 'The project code word is ALPHA-1.'] + F, 'Reply with the single word READY.')
b = one(cwd, ['--resume', sid, '--append-system-prompt', 'The project code word is BETA-2.'] + F, ASK)
c = one(cwd, ['--resume', sid] + F, ASK)
print(f'  first run -> {a!r}; continued with BETA-2 -> {b!r}; continued with no prompt -> {c!r}')
for f in glob.glob(os.path.join(H, 'projects', '*', sid + '*')):
    (shutil.rmtree if os.path.isdir(f) else os.remove)(f)
print('=== D3: where the processes of shell calls live (sampled 20 times a second)')
cwd = os.path.join(ROOT, 'bg3'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd); leader = pr.p.pid; seen = {}; stop = threading.Event()
def table():
    out = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid=,sess=,comm='], capture_output=True, text=True).stdout
    rows = {}
    for ln in out.splitlines():
        p = ln.split(None, 4)
        if len(p) >= 5:
            try: rows[int(p[0])] = (int(p[1]), int(p[2]), p[3], p[4][-40:])
            except ValueError: pass
    return rows
def sample():
    while not stop.is_set():
        rows = table(); desc = {leader}; changed = True
        while changed:
            changed = False
            for pid, (ppid, pgid, sess, comm) in rows.items():
                if ppid in desc and pid not in desc: desc.add(pid); changed = True
        for pid in desc:
            if pid != leader and pid in rows and pid not in seen:
                try: sid_ = os.getsid(pid)
                except Exception: sid_ = None
                seen[pid] = {'ppid': rows[pid][0], 'pgid': rows[pid][1], 'sid': sid_, 'comm': rows[pid][3]}
        time.sleep(0.05)
threading.Thread(target=sample, daemon=True).start()
pr.send(user("Run these three with your Bash tool, each as its own ordinary call, in this order: 1) `nohup sleep 61 >/dev/null 2>&1 & echo one` 2) `sleep 2; echo two` 3) `nohup sleep 62 >/dev/null 2>&1 & echo three`. Then reply with the single word DONE."))
r = pr.wait_for(lambda o: o.get('type') == 'result', 180); time.sleep(0.5); stop.set()
lsid = os.getsid(leader); lpg = os.getpgid(leader)
print('  claude: pid', leader, 'session', lsid, 'group', lpg)
for pid, d in sorted(seen.items()): print('  descendant seen:', pid, {k: v for k, v in d.items()}, '| session is claude\'s:', d['sid'] == lsid)
left = {}
for pat in ('sleep 61', 'sleep 62'):
    for p in alive(pat):
        try: left[p] = {'what': pat, 'parent': table().get(p, (None,))[0], 'pgid': os.getpgid(p), 'sid': os.getsid(p)}
        except Exception as e: left[p] = {'error': str(e)}
print('  detached processes while claude still runs:', left)
print('  their groups were seen among claude\'s descendants:', {p: (d.get('pgid') in {x['pgid'] for x in seen.values()}) for p, d in left.items()}, '| their sessions were seen:', {p: (d.get('sid') in {x['sid'] for x in seen.values()}) for p, d in left.items()})
try: pr.p.stdin.close()
except Exception: pass
try: rc = pr.p.wait(40)
except Exception: rc = 'still running'
time.sleep(1); after = [p for pat in ('sleep 61', 'sleep 62') for p in alive(pat)]
print('  claude exit:', rc, '| alive afterwards:', after)
for p in after:
    try: os.kill(p, signal.SIGKILL)
    except Exception: pass
print('  cleaned up:', not any(alive(x) for x in ('sleep 61', 'sleep 62')))
