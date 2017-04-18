from enum import Enum


class Currency(Enum):
    """Currencies that we use for payments. Maps currency to its code.

    Currently only in use with PayPal. List of all currencies supported by
    PayPal is available at https://developer.paypal.com/docs/classic/api/currency_codes/#paypal.

    Values of these must match ones that are defined in the `payment_currency`
    type in the database.
    """
    US_Dollar = "usd"
    Euro = "eur"
