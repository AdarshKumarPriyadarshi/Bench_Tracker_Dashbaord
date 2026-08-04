import copy


def update_dict(dict_to_update: dict, other_dict: dict) -> dict:
    """Updates first dict with the other.

    Doesn't reset values in the first dict, if they are None in the other.
    """
    updated_dict = copy.deepcopy(dict_to_update)

    for key, value in other_dict.items():
        if value is None:
            continue

        if isinstance(value, dict):
            updated_dict[key] = update_dict(dict_to_update.get(key, {}), value)
        else:
            updated_dict[key] = value

    return updated_dict
