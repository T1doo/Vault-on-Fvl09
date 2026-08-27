def classify_exclusive_relation(*, inside, on, beside):
    active = [name for name, value in (("inside", inside), ("on", on), ("beside", beside)) if bool(value)]
    return active[0] if len(active) == 1 else None
