from authlib.common.security import generate_token


def create_access_token(*args, **kwargs):
    return "mebo_" + generate_token(42)


def create_refresh_token(*args, **kwargs):
    return "mebr_" + generate_token(48)
