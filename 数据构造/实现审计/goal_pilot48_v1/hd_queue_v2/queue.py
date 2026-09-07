"""Scoped Git status recovery; preserve v1 runner and its failed evidence."""
import argparse
import signal
import subprocess
from pathlib import Path
from goal_pilot48_v1.hd_queue_v1 import queue as parent

HERE = Path(__file__).resolve().parent
PARENT_SOURCE = Path(parent.__file__).resolve()

class ScopedSubprocess:
    def __getattr__(self, name):
        return getattr(subprocess, name)

    def check_output(self, args, **kwargs):
        if args == ['git', '-C', str(parent.VAULT), 'status', '--porcelain']:
            args = [*args, '--untracked-files=normal', '--',
                    '数据构造/实现审计/goal_pilot48_v1',
                    '数据构造/正式数据构造日志.md']
            kwargs['timeout'] = 60
        return subprocess.check_output(args, **kwargs)

def configure():
    parent.HERE = HERE
    parent.PLAN = HERE / 'PLAN.json'
    parent.CURRENT = HERE / 'CURRENT.json'
    parent.EVENTS = HERE / 'events.jsonl'
    parent.__file__ = str(Path(__file__).resolve())
    parent.subprocess = ScopedSubprocess()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    configure()
    if args.prepare:
        parent.prepare()
        plan = parent.checked(parent.PLAN)
        plan.pop('receipt_sha256')
        plan['source_files'][str(PARENT_SOURCE)] = parent.sha(PARENT_SOURCE)
        plan['schema_version'] = 'finite_native_HD_display_queue_v2_scoped_git'
        plan['receipt_sha256'] = parent.budget.digest(plan)
        parent.budget.atomic(parent.PLAN, plan)
        return
    def interrupt(*_):
        raise KeyboardInterrupt('queue interrupted')
    signal.signal(signal.SIGTERM, interrupt)
    try:
        parent.run()
    except BaseException as exc:
        parent.emit('QUEUE_STOPPED', error=type(exc).__name__, message=str(exc))
        raise

if __name__ == '__main__':
    main()
