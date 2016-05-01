import six

AVAILABLE_SCOPES = [
    # Add new scopes there
]

STORAGE_SEPARATOR = ","


def validate_scopes(scopes):
    if not isinstance(scopes, list):
        raise ValueError("Scopes must be stored in a list")
    for scope in scopes:
        if not isinstance(scope, six.string_types):
            raise ValueError("Each scope must be a string")
        if scope not in AVAILABLE_SCOPES:
            raise ValueError("Unrecognized scope: %s" % scope)


def scopes_list_to_string(scopes):
    """Convert list of scopes for storage in the database.

    None can be passed to this function. None will be returned in that case.

    Args:
        scopes (list): List of scopes (as strings).

    Returns:
        str: String for insertion into the database.
    """
    if scopes:
        validate_scopes(scopes)
        return STORAGE_SEPARATOR.join(scopes)
    else:
        return None


def scopes_string_to_list(scopes):
    """Convert string with scopes that is stored in the database into a list.

    None can be passes to this function. In this case empty list will be returned.

    Args:
        scopes (str): String retrieved from the database.

    Returns:
        List of strings.
    """
    if scopes:
        return scopes.split(STORAGE_SEPARATOR)
    else:
        return []
