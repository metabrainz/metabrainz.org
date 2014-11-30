def reformat_datetime(value, format='%x %X %Z'):
    return value.strftime(format)
