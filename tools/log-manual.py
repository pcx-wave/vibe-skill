import json, datetime, subprocess, os

workdir = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True).stdout.strip() or os.getcwd()
project = os.path.basename(workdir.rstrip('/'))

stat = subprocess.run(['git','-C',workdir,'diff','--stat'], capture_output=True, text=True).stdout
lines_added = sum(
    int(l.split('+')[1].split()[0])
    for l in stat.splitlines()
    if '|' in l and '+' in l
) if stat else 0
files_changed = len([l for l in stat.splitlines() if '|' in l])

tokens_out = lines_added * 10
tokens_in  = lines_added * 40
cost = (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000

entry = {
    'ts': datetime.datetime.utcnow().isoformat() + 'Z',
    'delegate': 'claude-manual',
    'workdir': workdir, 'project': project,
    'exit_code': 0, 'files_changed': files_changed,
    'tokens_in': tokens_in, 'tokens_out': tokens_out,
    'tokens_total': tokens_in + tokens_out,
    'cost_usd': round(cost, 6), 'cost_estimated': True,
    'lines_added': lines_added,
}
log = os.path.expanduser('~/.local/share/delegate-runs.jsonl')
with open(log, 'a') as f:
    f.write(json.dumps(entry) + '\n')
print(f'[log] claude-manual -> {project}  ~{lines_added} lines added  est. cost ${cost:.4f}')
