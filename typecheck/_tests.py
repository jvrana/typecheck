from .check import validate_value


def fail_type_check():
    validate_value(5.0, int)
