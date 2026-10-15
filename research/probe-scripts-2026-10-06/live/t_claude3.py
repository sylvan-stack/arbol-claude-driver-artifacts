import sys, json, uuid, signal
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("print('=== T1a")[0])
def child(o): return bool(o.get('parent_tool_use_id'))
def brief(o):
    ty = o.get('type'); s = ('child ' if child(o) else 'main  ') + str(ty)
    if ty == 'system': s += ' ' + str(o.get('subtype')) + (' tasks=%d' % len(o.get('tasks') or []) if o.get('subtype') == 'background_tasks_changed' else '') + ((' status=' + str(o.get('status'))) if o.get('subtype') == 'task_notification' else '') + ((' patch=' + json.dumps(o.get('patch'))[:70]) if o.get('subtype') == 'task_updated' else '')
    elif ty in ('assistant', 'user'):
        c = o.get('message', {}).get('content')
        for b in (c if isinstance(c, list) else [{'type': 'text', 'text': str(c)}]):
            if b.get('type') == 'text': s += f" text={b.get('text','')[:70]!r}"
            elif b.get('type') == 'tool_use': s += f" tool_use:{b.get('name')}"
            elif b.get('type') == 'tool_result': s += f" tool_result err={b.get('is_error')} {str(b.get('content'))[:70]!r}"
    elif ty == 'result': s += f" {o.get('subtype')} terminal_reason={o.get('terminal_reason')} is_error={o.get('is_error')} text={str(o.get('result'))[:60]!r}"
    elif ty in ('control_response', 'control_request'): s += ' ' + json.dumps(o.get('response') or o.get('request'))[:140]
    return s
def timeline(pr, since=0):
    for t, o in pr.out:
        if t < since or o.get('_eof') or o.get('type') in ('stream_event', 'rate_limit_event') or (o.get('type') == 'system' and o.get('subtype') in ('thinking_tokens', 'status', 'commands_changed', 'task_progress')): continue
        if o.get('type') == 'assistant' and all(b.get('type') == 'thinking' for b in o.get('message', {}).get('content', [])): continue
        print(f'   {t:6.1f} {brief(o)}'[:230])
def alive(pattern):
    r = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True); return [int(x) for x in r.stdout.split()]

print('=== A: stop while a sub-agent works (claude)')
cwd = os.path.join(ROOT, 'stop'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd)
pr.send(user("Use the Agent tool to start exactly one sub-agent with this job: 'Run the shell command `sleep 47; echo late-result` with a timeout long enough, then report what it printed.' Then tell me in one short sentence that you are waiting."))
got = pr.wait_for(lambda o: o.get('type') == 'assistant' and child(o) and any(b.get('type') == 'tool_use' for b in o.get('message', {}).get('content', [])), 120)
time.sleep(2.0); t_int = time.monotonic() - pr.t0
print('sub-agent command running:', bool(got), '| sleep processes before the stop:', len(alive('sleep 47')))
pr.send({'type': 'control_request', 'request_id': 'int1', 'request': {'subtype': 'interrupt'}})
time.sleep(8); n_after_int = len(alive('sleep 47'))
try: pr.p.stdin.close()
except Exception: pass
try: rc = pr.p.wait(25)
except Exception: rc = 'still running 25 s after the input was closed'
left = alive('sleep 47')
print(f'stop sent at {t_int:.1f} s; sleep processes 8 s later: {n_after_int}; exit: {rc}; sleep processes after the exit: {len(left)}')
timeline(pr, since=t_int - 0.2)
for p in left:
    try: os.kill(p, signal.SIGKILL)
    except Exception: pass
if rc == 'still running 25 s after the input was closed':
    try: os.killpg(pr.p.pid, signal.SIGKILL)
    except Exception: pass

print('=== B: a question asked by a sub-agent (claude)')
asked = []
def answer(pr, req):
    r = req.get('request', {}); inp = r.get('input') or {}; asked.append({k: v for k, v in r.items() if k != 'input'})
    if r.get('tool_name') == 'AskUserQuestion':
        resp = {'behavior': 'allow', 'updatedInput': dict(inp, answers={q.get('question'): 'Pear' for q in inp.get('questions') or []})}
    else: resp = {'behavior': 'allow'}
    pr.send({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': req.get('request_id'), 'response': resp}})
cwd = os.path.join(ROOT, 'subq'); os.makedirs(cwd)
pr = Proc(STD + ['--permission-prompt-tool', 'stdio'], ENV, cwd)
pr.send(user("Use the Agent tool to start exactly one sub-agent with this job: 'Use the AskUserQuestion tool to ask the user one question, Which fruit?, with the options Apple and Pear. Then report the chosen option. If you have no AskUserQuestion tool, report NO-QUESTION-TOOL.' Do not ask me anything yourself. When the sub-agent has reported, reply with one line: SUBAGENT-SAID followed by its report."))
i = 0; end = time.monotonic() + 200; results = 0; tasks_left = None
while time.monotonic() < end:
    r = pr.wait_for(lambda o: o.get('type') in ('result', 'control_request') or (o.get('type') == 'system' and o.get('subtype') == 'background_tasks_changed'), max(1, end - time.monotonic()), start=i)
    if not r: break
    i = next(k for k, (t, o) in enumerate(pr.out) if o is r[1]) + 1
    if r[1]['type'] == 'control_request': answer(pr, r[1])
    elif r[1]['type'] == 'system': tasks_left = len(r[1].get('tasks') or [])
    else:
        results += 1
        if not tasks_left: break
rc = pr.close(10)
print('requests the tool sent:', json.dumps(asked)[:500]); timeline(pr); print('exit', rc)

print('=== C: a changed system prompt on a continued conversation (claude)')
cwd = os.path.join(ROOT, 'sysprompt'); os.makedirs(cwd); sid = str(uuid.uuid4())
BASE = [a for a in STD if a != '--no-session-persistence']
def one(extra, text):
    pr = Proc(BASE + extra, ENV, cwd); pr.send(user(text)); r = pr.wait_for(lambda o: o.get('type') == 'result', 120); pr.close(); return (r[1].get('result') if r else None), (r[1].get('is_error') if r else None)
print('  first run, prompt says ALPHA-1:', one(['--session-id', sid, '--append-system-prompt', 'The project code word is ALPHA-1.'], 'What is the project code word? Reply with the code word only.'))
print('  continued, prompt says BETA-2 :', one(['--resume', sid, '--append-system-prompt', 'The project code word is BETA-2.'], 'What is the project code word now, according to your system prompt? Reply with the code word only.'))
print('  continued, no prompt given    :', one(['--resume', sid], 'What is the project code word according to your system prompt? Reply with the code word only, or NONE if your system prompt names none.'))
import glob
for f in glob.glob(os.path.join(H, 'projects', '*', sid + '*')):
    (shutil.rmtree if os.path.isdir(f) else os.remove)(f)

print('=== D: a command put in the background, after claude has ended')
cwd = os.path.join(ROOT, 'bg'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd); leader = pr.p.pid
pr.send(user("Use your Bash tool with run_in_background set to true to start this command: `sleep 53`. Do not wait for it. Then reply with the single word STARTED."))
r = pr.wait_for(lambda o: o.get('type') == 'result', 120); time.sleep(1)
pids = alive('sleep 53'); info = []
for p in pids:
    try: info.append({'pid': p, 'same_session_as_claude': os.getsid(p) == os.getsid(leader), 'pgid_is_own': os.getpgid(p) == p, 'pgid_is_claudes': os.getpgid(p) == os.getpgid(leader)})
    except Exception as e: info.append({'pid': p, 'error': str(e)})
print('  while claude runs:', info, '| answer:', (r[1].get('result') if r else None))
sess = os.getsid(leader)
try: pr.p.stdin.close()
except Exception: pass
try: rc = pr.p.wait(40)
except Exception: rc = 'still running after 40 s'
after = alive('sleep 53'); info2 = []
for p in after:
    try: info2.append({'pid': p, 'session_is_claudes_old_session': os.getsid(p) == sess, 'parent': int(subprocess.run(['ps', '-o', 'ppid=', '-p', str(p)], capture_output=True, text=True).stdout or 0)})
    except Exception as e: info2.append({'pid': p, 'error': str(e)})
print('  claude exit:', rc, '| still alive afterwards:', info2)
timeline(pr, since=(r[0] if r else 0) - 0.1)
for p in after:
    try: os.kill(p, signal.SIGKILL)
    except Exception: pass
print('  cleaned up:', len(alive('sleep 53')) == 0)
