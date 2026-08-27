from ..signals import first_stable_true_frame


def completion_frame(slot_predicate_values, stability_frames):
    return first_stable_true_frame(slot_predicate_values, stability_frames)


def verify_completed_slots_preserved(before, after):
    completed = [name for name, value in before.items() if bool(value)]
    broken = [name for name in completed if not bool(after.get(name, False))]
    return {"pass": not broken, "broken_slots": broken}
