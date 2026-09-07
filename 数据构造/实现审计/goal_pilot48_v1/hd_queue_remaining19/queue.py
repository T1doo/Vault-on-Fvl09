"""Continue only the remaining unissued displays after v2 release reconciliation."""
from pathlib import Path
from goal_pilot48_v1.hd_queue_v2 import queue as previous

ORIGINAL_CONFIGURE = previous.configure
SOURCE = Path(__file__).resolve()
PREVIOUS_SOURCE = Path(previous.__file__).resolve()

def configure():
    ORIGINAL_CONFIGURE()
    parent = previous.parent
    parent.HERE = SOURCE.parent
    parent.PLAN = SOURCE.parent / 'PLAN.json'
    parent.CURRENT = SOURCE.parent / 'CURRENT.json'
    parent.EVENTS = SOURCE.parent / 'events.jsonl'
    parent.__file__ = str(SOURCE)

def main():
    previous.configure = configure
    # prepare() binds every imported implementation; run() rechecks those hashes.
    original_prepare = previous.parent.prepare
    def prepare():
        if previous.parent.budget.snapshot()['active_reservations']:
            raise ValueError('unresolved reservation')
        original_prepare()
        p = previous.parent.checked(previous.parent.PLAN)
        if len(p['items']) != 19:
            raise ValueError('remaining set differs from reviewed 19')
        p.pop('receipt_sha256')
        p['source_files'][str(PREVIOUS_SOURCE)] = previous.parent.sha(PREVIOUS_SOURCE)
        p['receipt_sha256'] = previous.parent.budget.digest(p)
        previous.parent.budget.atomic(previous.parent.PLAN, p)
    previous.parent.prepare = prepare
    previous.main()

if __name__ == '__main__':
    main()
