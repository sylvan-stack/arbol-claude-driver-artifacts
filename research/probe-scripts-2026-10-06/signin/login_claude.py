import os, subprocess, sys, time
HOME = os.path.expanduser('~'); S = "<this folder>"; H = os.environ.get("ARBOL_CLAUDE_SIGNED_HOME", os.path.join(os.path.expanduser("~"), "Library/Application Support/Arbol/drivers/arbol-claude-driver/subscriptions/test-anthropic/home"))
env = {'HOME': HOME, 'USER': os.environ.get('USER', os.path.basename(HOME)), 'LOGNAME': os.environ.get('USER', os.path.basename(HOME)), 'TMPDIR': os.environ.get('TMPDIR','/tmp'), 'LANG': 'en_US.UTF-8',
       'PATH': f'{HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin', 'CLAUDE_CONFIG_DIR': H, 'BROWSER': S + '/browser.sh'}
t0 = time.time()
p = subprocess.Popen([f'{HOME}/.local/bin/claude', 'auth', 'login', '--claudeai'], env=env, cwd=S, stdin=subprocess.PIPE, stdout=open(S + '/login.out', 'wb'), stderr=subprocess.STDOUT)
try: rc = p.wait(600)
except subprocess.TimeoutExpired:
    p.terminate(); rc = 'timeout after 10 minutes'
open(S + '/done', 'w').write(f'{rc} after {round(time.time()-t0)} s\n'); print('claude auth login ended:', rc, 'after', round(time.time()-t0), 's')
