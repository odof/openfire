# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def _get_values_diff(old_values, new_values):
    """
    Compare two dictionaries and return a dictionary of key-value pairs
    from the new_values dictionary where the values differ from those
    in the old_values dictionary.

    Args:
        old_values (dict): The original dictionary of values.
        new_values (dict): The updated dictionary of values.

    Returns:
        dict: A dictionary containing key-value pairs from new_values
            where the values are different from those in old_values.
    """
    return {key: new_values[key] for key in new_values if old_values.get(key) != new_values[key]}
