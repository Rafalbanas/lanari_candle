from app.db.models import ShippingMethod, CartDB

FREE_SHIPPING_THRESHOLD_PLN = 20000  # 200 PLN in grosze

SHIPPING_PRICES = {
    ShippingMethod.INPOST_LOCKER: 1499,
    ShippingMethod.COURIER: 1999,
    ShippingMethod.PICKUP: 0,
}


def get_cart_subtotal(cart: CartDB) -> int:
    """Sum of cart line totals in grosze."""
    subtotal = 0
    for item in cart.items:
        subtotal += item.qty * item.unit_price_pln
    return subtotal


def calculate_shipping(subtotal_pln: int, method: ShippingMethod) -> int:
    """Return shipping cost in grosze based on subtotal and method."""
    if method not in ShippingMethod:
        raise ValueError("Unknown shipping method")

    if method == ShippingMethod.PICKUP:
        return 0

    if subtotal_pln >= FREE_SHIPPING_THRESHOLD_PLN:
        return 0

    return SHIPPING_PRICES[method]
