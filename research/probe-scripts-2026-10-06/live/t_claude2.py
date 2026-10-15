import sys, json
sys.path.insert(0, '../probe')
from common import *
exec(open('t_claude.py').read().split("print('=== T1a")[0])
cwd = os.path.join(ROOT, 'subagent2'); os.makedirs(cwd)
pr = Proc(STD, ENV, cwd)
pr.send(user("Use the Agent tool to start exactly one sub-agent with this job: 'Run the shell command `echo sub-agent-says-PLUM` and report exactly what it printed.' When the sub-agent has finished, reply with one line: MAIN-DONE followed by what the sub-agent reported."))
first = pr.wait_for(lambda o: o.get('type') == 'result', 240)
t_first = first[0] if first else None
t_close = time.monotonic() - pr.t0
try: pr.p.stdin.close()
except Exception: pass
try: rc = pr.p.wait(240)
except Exception: rc = 'still running after 240 s'; os.killpg(pr.p.pid, 15)
time.sleep(0.5)
json.dump([[round(t, 2), o] for t, o in pr.out], open('subagent2.json', 'w'))
print('first result at', round(t_first, 1) if t_first else None, 's; input closed at', round(t_close, 1), 's; exit', rc, 'at', round(pr.out[-1][0], 1), 's')
for t, o in pr.out:
    ty = o.get('type'); p = 'child' if o.get('parent_tool_use_id') else 'main '
    if ty == 'stream_event' or (ty == 'system' and o.get('subtype') in ('thinking_tokens', 'status', 'commands_changed')) or ty == 'rate_limit_event' or o.get('_eof'): continue
    line = f'{t:6.1f} {p} {ty}'
    if ty == 'system':
        line += ' ' + str(o.get('subtype'))
        if o.get('subtype') == 'task_started': line += f" is_backgrounded={o.get('is_backgrounded')} task_type={o.get('task_type')} subagent_type={o.get('subagent_type')} spawn_depth={o.get('spawn_depth')}"
        if o.get('subtype') == 'background_tasks_changed': line += ' tasks=' + json.dumps([{k: v for k, v in x.items() if k in ('task_id', 'status', 'type', 'task_type', 'description')} if isinstance(x, dict) else x for x in (o.get('tasks') or [])])[:200]
        if o.get('subtype') == 'task_notification': line += f" status={o.get('status')} summary={str(o.get('summary'))[:60]!r}"
        if o.get('subtype') == 'task_updated': line += ' patch=' + json.dumps(o.get('patch'))[:120]
        if o.get('subtype') == 'init': line += f" session={str(o.get('session_id'))[:8]}"
    elif ty in ('assistant', 'user'):
        c = o.get('message', {}).get('content')
        for b in (c if isinstance(c, list) else [{'type': 'text', 'text': str(c)}]):
            bt = b.get('type')
            if bt == 'text': line += f" text={b.get('text','')[:70]!r}"
            elif bt == 'tool_use': line += f" tool_use:{b.get('name')} input_keys={sorted((b.get('input') or {}).keys())}" + (f" run_in_background={b['input'].get('run_in_background')}" if b.get('name') == 'Agent' else '')
            elif bt == 'tool_result': line += f" tool_result is_error={b.get('is_error')} " + (str(b.get('content'))[:90] if not isinstance(b.get('content'), list) else str([x.get('text', '')[:80] for x in b['content'] if isinstance(x, dict)])[:110])
            else: line += ' ' + str(bt)
    elif ty == 'result': line += f" subtype={o.get('subtype')} is_error={o.get('is_error')} num_turns={o.get('num_turns')} terminal_reason={o.get('terminal_reason')} cost={o.get('total_cost_usd')} session={str(o.get('session_id'))[:8]} text={str(o.get('result'))[:90]!r}"
    print(line[:330])
