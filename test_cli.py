import click
from client.saxo_client import SaxoClient
from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration

@click.command()
@click.option('--price', type=float, required=True, help='The price of the order')
@click.option('--code', type=str, required=True, help='The code of the order')
@click.option('--order-type', type=click.Choice(['limit', 'stop']), help='The order type', default="limit")
def set_order(price, code, order_type):
    click.echo(f'Setting order price to {price} and code to {code}')
    # Your code to handle the order goes here

@click.command()
def auth():
    click.echo(f'Setting order price to {price} and code to {code}')


if __name__ == '__main__':
    pass
    #set_order()
#    client = SaxoClient()
#    SaxoAuthClient(Configuration()).plouf()
#     print(client.get_stock("cap", "xpar"))
