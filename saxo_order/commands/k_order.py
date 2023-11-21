import click

import saxo_order.commands.auth as auth
import saxo_order.commands.available_funds as available_funds
import saxo_order.commands.get_report as get_report
import saxo_order.commands.search as search
import saxo_order.commands.set_oco_order as set_oco_order
import saxo_order.commands.set_order as set_order
import saxo_order.commands.set_stop_limit_order as set_stop_limit_order


@click.group()
def k_order():
    pass


k_order.add_command(auth.auth)
k_order.add_command(available_funds.available_funds)
k_order.add_command(get_report.get_report)
k_order.add_command(search.search)
k_order.add_command(set_oco_order.set_oco_order)
k_order.add_command(set_order.set_order)
k_order.add_command(set_stop_limit_order.set_stop_limit_order)
