"""Persist real command results and immutable failure evidence; never pass secrets."""
import datetime
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
label, *command = sys.argv[1:]
for folder in ('reports', 'bugs', 'screenshots'):
    (root / folder).mkdir(exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime('%Y%m%d-%H%M%S-%f')
print(f'Stage: {label} · {stamp} Asia/Kolkata', flush=True)
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
lines = []
for line in result.stdout:
    lines.append(line)
    print(line, end='', flush=True)
result.wait()
transcript = f'Stage: {label}\nTime: {stamp} Asia/Kolkata\nExit: {result.returncode}\n\n' + ''.join(lines)
(root / 'reports' / f'{stamp}-{label}.txt').write_text(transcript)
if result.returncode:
    (root / 'bugs' / f'{stamp}-{label}-FAILURE.txt').write_text(transcript)
    with (root / 'BUILDER_LOG.md').open('a') as log:
        log.write(f'\n### {stamp} — failure: {label}\n\nCommand exited {result.returncode}. Full original diagnostic saved in bugs/{stamp}-{label}-FAILURE.txt. Investigation and fix follow; evidence retained.\n')
print(f'Exit: {result.returncode}', flush=True)
sys.exit(result.returncode)