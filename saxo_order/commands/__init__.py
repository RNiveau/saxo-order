import click

from functools import wraps, partial


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            print(e)
            raise click.Abort()

    return wrapper


def config_option(func):
    return click.option(
        "--config",
        type=str,
        required=True,
        default="config.yml",
        envvar='SAXO_CONFIG',
        help="The path to config file",
    )(func)


def command_common_options(func):
    func = click.option(
        "--code",
        type=str,
        required=True,
        help="The code of the stock",
        prompt="What is the code of the product ?",
    )(func)
    func = click.option(
        "--country-code",
        type=str,
        required=True,
        default="xpar",
        help="The country code of the stock",
    )(func)
    func = click.option(
        "--quantity",
        type=int,
        required=True,
        help="The wanted quantity of stocks",
        prompt="What is the quantity of product ?",
    )(func)
    return func
