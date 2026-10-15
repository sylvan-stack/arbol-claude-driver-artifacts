import sys, json
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split('def shape')[0])
cwd = os.path.join(ROOT, 'bgshell'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd)
pr.send(user("Use your Bash tool with run_in_background set to true to start this command: `sleep 12; echo bg-finished`. Do not wait for it and do not check on it. Reply with the single word STARTED. If you are later told that the command has finished, reply with the single word NOTICED."))
end = time.monotonic() + 60; i = 0; results = []
while time.monotonic() < end and len(results) < 2:
    with pr.lock:
        new = pr.out[i:]; i = len(pr.out)
    for t, o in new:
        if o.get('type') == 'system' and o.get('subtype') != 'init' and 'task' in str(o.get('subtype')):
            print(f'{t:6.1f} SHELL', json.dumps({k: v for k, v in o.items() if k not in ('uuid', 'session_id')})[:700])
        elif o.get('type') == 'system': print(f'{t:6.1f} system {o.get("subtype")}')
        elif o.get('type') == 'result': results.append(o); print(f'{t:6.1f} result #{len(results)} text={o.get("result")!r} is_error={o.get("is_error")}')
    time.sleep(0.2)
print('results with the input kept open:', len(results)); print('exit:', pr.close())
