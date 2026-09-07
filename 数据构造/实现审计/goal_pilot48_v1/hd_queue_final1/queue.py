"""Final single-item continuation after the reviewed F4-BAC late release."""
from pathlib import Path
from goal_pilot48_v1.hd_queue_v2 import queue as previous

HERE = Path(__file__).resolve().parent

def configure():
    previous.configure()
    parent = previous.parent
    parent.HERE = HERE
    parent.PLAN = HERE / 'PLAN.json'
    parent.CURRENT = HERE / 'CURRENT.json'
    parent.EVENTS = HERE / 'events.jsonl'
    parent.__file__ = str(Path(__file__).resolve())

def main():
    configure()
    previous.parent.run()

if __name__ == '__main__':
    main()
