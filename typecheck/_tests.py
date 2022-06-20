from .check import validate_args
from .check import validate_value


def fail_type_check():
    validate_value(5.0, int)


@validate_args
def for_readable_error_on_function(a: int) -> float:
    ...
