from .store_data import (
    CATEGORIES,
    STORE_LOCK,
    get_active_account,
    lookup_pincode,
)


def clickcart_globals(request):
    """Inject global navigation, cart, wishlist, compare, and account context without DB."""
    with STORE_LOCK:
        account = get_active_account(request)
        cart_count = sum(int(i.get('quantity', 1)) for i in account.get('cart', []))
        wishlist_ids = set(account.get('wishlist', []))
        compare_ids = list(account.get('compare', []))
        unread_notifications_count = sum(
            1 for n in account.get('notifications', []) if not n.get('is_read', False)
        )
        pincode = request.session.get('cc_pincode', '560001')
        pincode_info = lookup_pincode(pincode) or lookup_pincode('560001')

        return {
            'cc_user': account,
            'cart_count': cart_count,
            'wishlist_count': len(wishlist_ids),
            'wishlist_product_ids': wishlist_ids,
            'compare_ids': compare_ids,
            'compare_count': len(compare_ids),
            'unread_notifications_count': unread_notifications_count,
            'nav_categories': CATEGORIES,
            'selected_pincode': pincode_info['pincode'],
            'selected_pincode_info': pincode_info,
            'supercoins_balance': account.get('supercoins', 0),
        }
