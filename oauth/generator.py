from authlib.common.security import generate_token


def create_access_token(*args, **kwargs):
    return "meba_" + generate_token(42)


def create_refresh_token(*args, **kwargs):
    return "mebr_" + generate_token(48)


def create_client_secret(*args, **kwargs):
    return "mebs_" + generate_token(48)


def create_client_id(*args, **kwargs):
    return generate_token(24)
