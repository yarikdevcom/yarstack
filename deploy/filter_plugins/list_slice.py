def list_slice(value, from_, to_):
    return value[int(from_): int(to_)]


class FilterModule:
    def filters(self):
        return {
            "list_slice": list_slice,
        }
