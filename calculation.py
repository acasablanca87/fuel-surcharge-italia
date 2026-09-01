"""Funzioni pure per i calcoli del fuel surcharge.

Questo modulo non dipende da Streamlit: rende la formula verificabile con
test automatici e riutilizzabile da eventuali esportazioni future.
"""


def calculate_surcharge(
    target_price: float, current_price: float, fuel_weight_pct: int
) -> tuple[float, float, float]:
    """Restituisce differenza in euro, variazione % e surcharge %.

    ``fuel_weight_pct`` è espresso come percentuale intera, ad esempio 30.
    """
    if target_price <= 0:
        raise ValueError("Il prezzo target deve essere maggiore di zero.")
    if current_price < 0:
        raise ValueError("Il prezzo rilevato non può essere negativo.")
    if not 1 <= fuel_weight_pct <= 100:
        raise ValueError("L'incidenza del gasolio deve essere compresa tra 1 e 100.")

    delta_price = current_price - target_price
    delta_price_pct = (delta_price / target_price) * 100
    surcharge_pct = delta_price_pct * (fuel_weight_pct / 100)
    return delta_price, delta_price_pct, surcharge_pct


def price_bracket(
    target_price: float, surcharge_pct: float, fuel_weight_pct: int
) -> tuple[float, float]:
    """Calcola i limiti di prezzo della fascia centrata sul surcharge indicato."""
    if target_price <= 0:
        raise ValueError("Il prezzo target deve essere maggiore di zero.")
    if not 1 <= fuel_weight_pct <= 100:
        raise ValueError("L'incidenza del gasolio deve essere compresa tra 1 e 100.")

    lower_surcharge = surcharge_pct - 0.25
    upper_surcharge = surcharge_pct + 0.25
    return (
        target_price * (1 + (lower_surcharge / fuel_weight_pct)),
        target_price * (1 + (upper_surcharge / fuel_weight_pct)),
    )
