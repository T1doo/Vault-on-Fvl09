from ..signals import first_stable_true_frame


def completion_frame(slot_predicate_values, stability_frames):
    return first_stable_true_frame(slot_predicate_values, stability_frames)
