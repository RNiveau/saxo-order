import click

from functools import wraps, partial
from client.saxo_client import SaxoClient


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            print(e)
            click.Abort()

    return wrapper


def select_account(client: SaxoClient) -> str:
    accounts = client.get_accounts()
    prompt = "Select the account (select with ID):\n"
    for account in accounts["Data"]:
        if "DisplayName" in account:
            prompt += f"- {account['DisplayName']} | {account['AccountId']}\n"
        else:
            prompt += f"- NoName | {account['AccountId']}\n"
    id = input(prompt)
    account = list(filter(lambda x: x["AccountId"] == id, accounts["Data"]))
    if len(account) != 1:
        raise SaxoException("Wrong account selection")
    return account[0]["AccountKey"]
