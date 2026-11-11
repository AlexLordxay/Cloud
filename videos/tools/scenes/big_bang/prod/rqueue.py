# A render queue: runs the segments listed in prod/queue.txt one after another (each as prod/run.py <seg>), skipping
# those already finished (render_<seg>.log ends with «done»). Re-reads the list, so segments can be appended while it
# runs; idles when nothing is left.   nohup python3 prod/rqueue.py > render_queue.log 2>&1 &
import os, subprocess, time
BB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(BB, 'prod', 'queue.txt')
NEEDS = {'seg02': ['seg01']}            # a segment that starts from another's frame waits for it


def finished(seg):
    p = os.path.join(BB, f'render_{seg}.log')
    return os.path.exists(p) and open(p).read().rstrip().endswith('done')


while True:
    segs = [l.strip() for l in open(Q) if l.strip() and not l.startswith('#')] if os.path.exists(Q) else []
    todo = [s for s in segs if not finished(s) and all(finished(d) for d in NEEDS.get(s, []))]
    if not todo:
        time.sleep(20); continue
    s = todo[0]
    print(time.strftime('%H:%M:%S'), 'start', s, flush=True)
    with open(os.path.join(BB, f'render_{s}.log'), 'a') as log:
        r = subprocess.run(['python3', os.path.join(BB, 'prod', 'run.py'), s], cwd=BB, stdout=log, stderr=subprocess.STDOUT)
    print(time.strftime('%H:%M:%S'), 'end', s, r.returncode, flush=True)
    if r.returncode != 0:
        # move a failing segment to the end of the list (it will be retried after the others; check its log)
        segs.remove(s); segs.append(s)
        open(Q, 'w').write('\n'.join(segs) + '\n')
        time.sleep(60)
