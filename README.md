# saxo-order

The main goal of this project is to ease the setup of asset orders and to ease the reporting
I currently support saxo bank and binance (only for the report)

The reporting is sent to a private google sheet

## Saxo

### Available commands

**auth**: Authentification workflow with saxo api. We need to call it first before to use saxo commands

**available-funds**: Select one account and show how many funds are available to set up an order. It takes in account current opened orders.

**get-report**: From the date to now for a specific account, list all orders. It updates the gsheet according to these orders

**search**: Search assets in the saxo database according to a keywork. List stocks, cfd and turbos

**set**: Set an order and write the report in the gsheet. See the subcommand to have more details

**shortcut**: Shortcut for cfd on indexes. It's the same commands than *set* but it allows to go faster and bypass the validation

Available indexes are:
* SP500
* DAX
* CAC40
* Russel2000
* Nasdaq
* Nikkei

## Binance

### Available commands

**get-report**: From the date to now, list all orders related to crypto currencies (hardcoded list for now)

## Miscellaneous

**get-score**: Based on zone bourse, scan financial data to calculate a score. The score is helpful to understand if a stock is interesting for a long term vision or not.