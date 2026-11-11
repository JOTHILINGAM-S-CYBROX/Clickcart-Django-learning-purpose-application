from datetime import date, datetime, timedelta
import copy
import math
import uuid

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .store_data import (
    BANK_OFFERS,
    CATEGORIES,
    CATEGORY_MAP,
    COUPONS,
    HERO_BANNERS,
    ORDER_FLOW,
    STORE,
    STORE_LOCK,
    add_item_to_cart,
    compute_cart_summary,
    enrich_product,
    get_active_account,
    get_all_products,
    get_product_by_slug,
    get_visitor_id,
    lookup_pincode,
    merge_guest_into_user,
)


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') == '1'


def _safe_next(request, default='home'):
    nxt = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER')
    if nxt and nxt.startswith('/'):
        return nxt
    return default


def home(request):
    """Clickcart Flipkart-style home landing page."""
    products = get_all_products()
    account = get_active_account(request)

    deals_of_day = [p for p in products if p.get('is_deal_of_day')][:8]
    top_mobiles = [p for p in products if p['category_slug'] == 'mobiles'][:4]
    best_electronics = [p for p in products if p['category_slug'] == 'electronics'][:6]
    fashion_picks = [p for p in products if p['category_slug'] == 'fashion'][:4]
    appliances_home = [p for p in products if p['category_slug'] in ('appliances', 'home-furniture')][:6]
    trending_products = sorted(products, key=lambda x: (x.get('is_trending', False), x['sold_count']), reverse=True)[:8]

    prod_map = {p['id']: p for p in products}
    recently_viewed = [prod_map[pid] for pid in account.get('recently_viewed', []) if pid in prod_map][:6]

    context = {
        'categories': CATEGORIES,
        'hero_banners': HERO_BANNERS,
        'bank_offers': BANK_OFFERS,
        'deals_of_day': deals_of_day,
        'top_mobiles': top_mobiles,
        'best_electronics': best_electronics,
        'fashion_picks': fashion_picks,
        'appliances_home': appliances_home,
        'trending_products': trending_products,
        'recently_viewed': recently_viewed,
        'coupons': COUPONS,
    }
    return render(request, 'landingpage/home.html', context)


def product_list(request):
    """Catalog search, multi-faceted filtering, sorting, and pagination."""
    all_products = get_all_products()

    q = (request.GET.get('q') or '').strip()
    cat_slug = (request.GET.get('category') or '').strip()
    selected_brands = [b.strip() for b in request.GET.getlist('brand') if b.strip()]
    min_price = (request.GET.get('min_price') or '').strip()
    max_price = (request.GET.get('max_price') or '').strip()
    min_rating = (request.GET.get('min_rating') or '').strip()
    min_discount = (request.GET.get('min_discount') or '').strip()
    only_assured = request.GET.get('assured') == '1'
    only_exchange = request.GET.get('exchange') == '1'
    only_fast = request.GET.get('fast') == '1'
    only_deal = request.GET.get('deal') == '1'
    sort_by = (request.GET.get('sort') or 'relevance').strip()

    if cat_slug and cat_slug != 'top-offers':
        brand_pool = [p['brand'] for p in all_products if p['category_slug'] == cat_slug]
    else:
        brand_pool = [p['brand'] for p in all_products]
    available_brands = sorted(set(brand_pool))

    filtered = all_products

    if cat_slug == 'top-offers':
        filtered = [p for p in filtered if p['discount_percent'] >= 20 or p.get('is_deal_of_day')]
    elif cat_slug and cat_slug in CATEGORY_MAP:
        filtered = [p for p in filtered if p['category_slug'] == cat_slug]

    if q:
        ql = q.lower()
        filtered = [
            p for p in filtered
            if ql in p['title'].lower()
            or ql in p['brand'].lower()
            or ql in p['category_name'].lower()
            or ql in p['short_description'].lower()
        ]

    if selected_brands:
        sb_lower = {b.lower() for b in selected_brands}
        filtered = [p for p in filtered if p['brand'].lower() in sb_lower]

    if min_price.isdigit():
        filtered = [p for p in filtered if p['selling_price'] >= int(min_price)]
    if max_price.isdigit():
        filtered = [p for p in filtered if p['selling_price'] <= int(max_price)]

    if min_rating:
        try:
            mr = float(min_rating)
            filtered = [p for p in filtered if float(p['rating_avg']) >= mr]
        except ValueError:
            pass

    if min_discount.isdigit():
        md = int(min_discount)
        filtered = [p for p in filtered if p['discount_percent'] >= md]

    if only_assured:
        filtered = [p for p in filtered if p.get('is_assured')]
    if only_exchange:
        filtered = [p for p in filtered if p.get('is_exchange_available')]
    if only_fast:
        filtered = [p for p in filtered if p.get('is_fast_delivery')]
    if only_deal:
        filtered = [p for p in filtered if p.get('is_deal_of_day')]

    if sort_by == 'price_asc':
        filtered.sort(key=lambda p: p['selling_price'])
    elif sort_by == 'price_desc':
        filtered.sort(key=lambda p: p['selling_price'], reverse=True)
    elif sort_by == 'rating':
        filtered.sort(key=lambda p: (float(p['rating_avg']), p['rating_count']), reverse=True)
    elif sort_by == 'discount':
        filtered.sort(key=lambda p: p['discount_percent'], reverse=True)
    elif sort_by == 'newest':
        filtered.sort(key=lambda p: p['id'], reverse=True)
    else:
        filtered.sort(key=lambda p: (p.get('is_trending', False), p['sold_count']), reverse=True)

    per_page = 12
    total_count = len(filtered)
    total_pages = max(1, math.ceil(total_count / per_page))
    try:
        page = max(1, min(total_pages, int(request.GET.get('page', 1))))
    except ValueError:
        page = 1
    start = (page - 1) * per_page
    page_products = filtered[start:start + per_page]

    active_category = CATEGORY_MAP.get(cat_slug)
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'products': page_products,
        'total_count': total_count,
        'page': page,
        'total_pages': total_pages,
        'page_range': range(1, total_pages + 1),
        'query_string': query_params.urlencode(),
        'q': q,
        'cat_slug': cat_slug,
        'active_category': active_category,
        'available_brands': available_brands,
        'selected_brands': selected_brands,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
        'min_discount': min_discount,
        'only_assured': only_assured,
        'only_exchange': only_exchange,
        'only_fast': only_fast,
        'only_deal': only_deal,
        'sort_by': sort_by,
        'categories': CATEGORIES,
    }
    return render(request, 'landingpage/product_list.html', context)


def product_detail(request, slug):
    """Full Flipkart-style product page with variants, pincode check, reviews, Q&A, and actions."""
    product = get_product_by_slug(slug)
    if not product:
        messages.error(request, 'Sorry, that product could not be found.')
        return redirect('product_list')

    with STORE_LOCK:
        account = get_active_account(request)
        pid = product['id']
        rv = account.setdefault('recently_viewed', [])
        if pid in rv:
            rv.remove(pid)
        rv.insert(0, pid)
        account['recently_viewed'] = rv[:12]

    if request.method == 'POST':
        action = request.POST.get('action')
        with STORE_LOCK:
            target = next((p for p in STORE.products if p['id'] == product['id']), None)
            if target and action == 'add_review':
                rating = max(1, min(5, int(request.POST.get('rating', 5) or 5)))
                title = (request.POST.get('title') or '').strip() or 'Great Product!'
                comment = (request.POST.get('comment') or '').strip()
                reviewer = account['name'] if account.get('is_authenticated') else (request.POST.get('reviewer_name') or 'Verified Buyer').strip()
                if comment:
                    STORE.next_review_id += 1
                    target['reviews'].insert(0, {
                        'id': STORE.next_review_id,
                        'user_name': reviewer,
                        'rating': rating,
                        'title': title,
                        'comment': comment,
                        'is_verified_purchase': bool(account.get('is_authenticated')),
                        'helpful_count': 0,
                        'created_at': 'Just now',
                    })
                    avg = sum(r['rating'] for r in target['reviews']) / len(target['reviews'])
                    target['rating_avg'] = round(avg, 1)
                    target['rating_count'] += 1
                    messages.success(request, 'Thank you! Your rating & review has been published.')
            elif target and action == 'helpful_review':
                rid = int(request.POST.get('review_id', 0) or 0)
                for r in target['reviews']:
                    if r['id'] == rid:
                        r['helpful_count'] += 1
                        break
            elif target and action == 'ask_question':
                qtext = (request.POST.get('question') or '').strip()
                asker = account['name'] if account.get('is_authenticated') else 'Clickcart Customer'
                if qtext:
                    STORE.next_question_id += 1
                    target['questions'].insert(0, {
                        'id': STORE.next_question_id,
                        'user_name': asker,
                        'question': qtext,
                        'answer': f"Thank you for asking! Our seller ({target['seller_name']}) confirms this item comes with {target['warranty_summary']} and {target['return_policy_days']}-day replacement.",
                        'answered_by': target['seller_name'],
                        'upvotes': 1,
                    })
                    messages.success(request, 'Question posted! Seller response added.')
            elif target and action == 'upvote_question':
                qid = int(request.POST.get('question_id', 0) or 0)
                for qa in target['questions']:
                    if qa['id'] == qid:
                        qa['upvotes'] += 1
                        break
        return redirect('product_detail', slug=slug)

    all_products = get_all_products()
    similar_products = [
        p for p in all_products
        if p['category_slug'] == product['category_slug'] and p['id'] != product['id']
    ][:4]
    if len(similar_products) < 4:
        extras = [p for p in all_products if p['id'] != product['id'] and p not in similar_products]
        similar_products.extend(extras[:4 - len(similar_products)])

    context = {
        'product': product,
        'similar_products': similar_products,
        'coupons': COUPONS,
        'bank_offers': BANK_OFFERS,
    }
    return render(request, 'landingpage/product_detail.html', context)


def search_suggest(request):
    """JSON live search autocomplete endpoint."""
    q = (request.GET.get('q') or '').strip().lower()
    if len(q) < 1:
        return JsonResponse({'suggestions': []})

    suggestions = []
    for c in CATEGORIES:
        if q in c['name'].lower():
            suggestions.append({
                'type': 'Category',
                'title': f"in {c['name']}",
                'url': f"/products/?category={c['slug']}",
                'image': f"/static/{c['icon_image']}",
                'price': '',
            })

    for p in get_all_products():
        if q in p['title'].lower() or q in p['brand'].lower() or q in p['category_name'].lower():
            suggestions.append({
                'type': p['brand'],
                'title': p['title'],
                'url': f"/product/{p['slug']}/",
                'image': f"/static/{p['primary_image']}",
                'price': f"₹{p['selling_price']:,}",
            })
        if len(suggestions) >= 8:
            break

    return JsonResponse({'suggestions': suggestions[:8]})


def check_pincode(request):
    """Validate and save user's delivery pincode."""
    pincode = (request.POST.get('pincode') or request.GET.get('pincode') or '').strip()
    info = lookup_pincode(pincode)
    if not info:
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'error': 'Please enter a valid 6-digit Indian pincode.'}, status=400)
        messages.error(request, 'Please enter a valid 6-digit Indian pincode.')
        return redirect(_safe_next(request))

    request.session['cc_pincode'] = info['pincode']
    if _is_ajax(request):
        return JsonResponse({'ok': True, 'data': info})
    messages.success(request, f"Delivery pincode updated to {info['pincode']} ({info['city']}).")
    return redirect(_safe_next(request))


def cart_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        summary = compute_cart_summary(account)
        products = get_all_products()
        recommended = [p for p in products if p.get('is_deal_of_day')][:4]

    return render(request, 'landingpage/cart.html', {
        'summary': summary,
        'coupons': COUPONS,
        'recommended': recommended,
    })


def cart_add(request, product_id):
    variant_id = request.POST.get('variant_id') or request.GET.get('variant_id')
    variant_id = int(variant_id) if str(variant_id).isdigit() else None
    qty = request.POST.get('quantity') or request.GET.get('quantity') or '1'
    qty = int(qty) if str(qty).isdigit() else 1
    with_exchange = (request.POST.get('with_exchange') or request.GET.get('with_exchange')) == '1'
    buy_now = (request.POST.get('buy_now') or request.GET.get('buy_now')) == '1'

    with STORE_LOCK:
        account = get_active_account(request)
        ok, msg = add_item_to_cart(account, product_id, variant_id=variant_id, quantity=qty, with_exchange=with_exchange)
        summary = compute_cart_summary(account)

    if _is_ajax(request):
        return JsonResponse({'ok': ok, 'message': msg, 'cart_count': summary['item_count']})

    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    if buy_now and ok:
        return redirect('checkout')
    if request.POST.get('redirect_to') == 'cart':
        return redirect('cart')
    return redirect(_safe_next(request, default='cart'))


@require_POST
def cart_update(request, item_id):
    action = request.POST.get('action', '')
    with STORE_LOCK:
        account = get_active_account(request)
        cart = account['cart']
        saved = account['saved_for_later']

        if action == 'move_to_cart':
            target = next((i for i in saved if i['item_id'] == item_id), None)
            if target:
                saved.remove(target)
                add_item_to_cart(account, target['product_id'], variant_id=target.get('variant_id'), quantity=1)
                messages.success(request, 'Item moved back to your cart.')
        elif action == 'remove_saved':
            account['saved_for_later'] = [i for i in saved if i['item_id'] != item_id]
            messages.info(request, 'Removed from Saved for Later.')
        else:
            target = next((i for i in cart if i['item_id'] == item_id), None)
            if target:
                if action == 'inc':
                    target['quantity'] = min(10, target['quantity'] + 1)
                elif action == 'dec':
                    if target['quantity'] > 1:
                        target['quantity'] -= 1
                    else:
                        cart.remove(target)
                        messages.info(request, 'Item removed from cart.')
                elif action == 'remove':
                    cart.remove(target)
                    messages.info(request, 'Item removed from cart.')
                elif action == 'save_for_later':
                    cart.remove(target)
                    saved.insert(0, {
                        'item_id': target['item_id'],
                        'product_id': target['product_id'],
                        'variant_id': target.get('variant_id'),
                    })
                    messages.success(request, 'Item saved for later.')
                elif action == 'toggle_exchange':
                    target['with_exchange'] = not target.get('with_exchange', False)
                    messages.success(request, 'Exchange option updated.')

    return redirect('cart')


@require_POST
def cart_coupon(request):
    action = request.POST.get('action', 'apply')
    with STORE_LOCK:
        account = get_active_account(request)
        if action == 'remove':
            account['applied_coupon'] = ''
            messages.info(request, 'Coupon removed.')
        elif action == 'toggle_coins':
            account['use_supercoins'] = not account.get('use_supercoins', False)
            state = 'applied' if account['use_supercoins'] else 'removed'
            messages.success(request, f'SuperCoins redemption {state}.')
        else:
            code = (request.POST.get('code') or '').strip().upper()
            account['applied_coupon'] = code
            summary = compute_cart_summary(account)
            if summary['coupon_discount'] > 0:
                messages.success(request, summary['coupon_msg'])
            else:
                messages.warning(request, summary['coupon_msg'] or 'Coupon cannot be applied to your current cart.')
    return redirect(_safe_next(request, default='cart'))


def wishlist_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        wids = list(account.get('wishlist', []))
    prod_map = {p['id']: p for p in get_all_products()}
    items = [prod_map[pid] for pid in wids if pid in prod_map]
    return render(request, 'landingpage/wishlist.html', {'items': items})


def wishlist_toggle(request, product_id):
    pid = int(product_id)
    with STORE_LOCK:
        account = get_active_account(request)
        wlist = account.setdefault('wishlist', [])
        if pid in wlist:
            wlist.remove(pid)
            added = False
            msg = 'Removed from your Wishlist.'
        else:
            wlist.insert(0, pid)
            added = True
            msg = 'Added to your Wishlist!'
        wcount = len(wlist)

    if _is_ajax(request):
        return JsonResponse({'ok': True, 'added': added, 'wishlist_count': wcount, 'message': msg})
    messages.success(request, msg)
    return redirect(_safe_next(request, default='wishlist'))


def compare_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        cids = list(account.get('compare', []))
    prod_map = {p['id']: p for p in get_all_products()}
    items = [prod_map[pid] for pid in cids if pid in prod_map]

    spec_keys = []
    for p in items:
        for k in p.get('specifications', {}).keys():
            if k not in spec_keys:
                spec_keys.append(k)

    return render(request, 'landingpage/compare.html', {
        'items': items,
        'spec_keys': spec_keys,
    })


def compare_toggle(request, product_id):
    pid = int(product_id)
    with STORE_LOCK:
        account = get_active_account(request)
        clist = account.setdefault('compare', [])
        if pid in clist:
            clist.remove(pid)
            added = False
            msg = 'Removed from Compare.'
        elif len(clist) >= 4:
            added = False
            msg = 'You can compare up to 4 products at a time.'
        else:
            clist.append(pid)
            added = True
            msg = 'Added to Compare list.'
        ccount = len(clist)

    if _is_ajax(request):
        return JsonResponse({'ok': True, 'added': added, 'compare_count': ccount, 'message': msg})
    messages.info(request, msg)
    return redirect(_safe_next(request, default='compare'))


def compare_clear(request):
    with STORE_LOCK:
        account = get_active_account(request)
        account['compare'] = []
    messages.info(request, 'Comparison list cleared.')
    return redirect('compare')


def checkout_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        summary = compute_cart_summary(account)
        if not summary['items']:
            messages.warning(request, 'Your cart is empty. Add items before checking out.')
            return redirect('cart')

        if request.method == 'POST':
            action = request.POST.get('action', 'place_order')

            if action == 'add_address':
                full_name = (request.POST.get('full_name') or '').strip()
                phone = (request.POST.get('phone') or '').strip()
                pincode = (request.POST.get('pincode') or '').strip()
                locality = (request.POST.get('locality') or '').strip()
                street = (request.POST.get('street_address') or '').strip()
                city = (request.POST.get('city') or '').strip()
                state = (request.POST.get('state') or '').strip()
                atype = request.POST.get('address_type', 'HOME')
                if full_name and phone and pincode and street and city:
                    new_addr = {
                        'id': f'addr-{uuid.uuid4().hex[:6]}',
                        'full_name': full_name,
                        'phone': phone,
                        'pincode': pincode,
                        'locality': locality or city,
                        'street_address': street,
                        'city': city,
                        'state': state or 'India',
                        'landmark': (request.POST.get('landmark') or '').strip(),
                        'address_type': atype,
                        'is_default': True,
                    }
                    for a in account['addresses']:
                        a['is_default'] = False
                    account['addresses'].insert(0, new_addr)
                    request.session['cc_pincode'] = pincode
                    messages.success(request, 'Delivery address saved!')
                else:
                    messages.error(request, 'Please fill all required address fields.')
                return redirect('checkout')

            if action == 'place_order':
                addr_id = request.POST.get('selected_address_id')
                selected_addr = next((a for a in account['addresses'] if a['id'] == addr_id), None)
                if not selected_addr and account['addresses']:
                    selected_addr = account['addresses'][0]

                if not selected_addr:
                    full_name = (request.POST.get('guest_name') or 'Guest Customer').strip()
                    phone = (request.POST.get('guest_phone') or '9876543210').strip()
                    pincode = (request.POST.get('guest_pincode') or request.session.get('cc_pincode', '560001')).strip()
                    street = (request.POST.get('guest_street') or '100 Main Market Road').strip()
                    city = (request.POST.get('guest_city') or 'Bengaluru').strip()
                    state = (request.POST.get('guest_state') or 'Karnataka').strip()
                    selected_addr = {
                        'id': f'addr-{uuid.uuid4().hex[:6]}',
                        'full_name': full_name,
                        'phone': phone,
                        'pincode': pincode,
                        'locality': city,
                        'street_address': street,
                        'city': city,
                        'state': state,
                        'landmark': '',
                        'address_type': 'HOME',
                        'is_default': True,
                    }
                    account['addresses'].append(selected_addr)

                payment_method = request.POST.get('payment_method', 'UPI')
                payable = summary['payable_total']

                if payment_method == 'WALLET' and account.get('wallet_balance', 0) < payable:
                    messages.error(request, 'Insufficient Clickcart Wallet balance. Please choose another payment method or top up your wallet.')
                    return redirect('checkout')

                if payment_method == 'WALLET':
                    account['wallet_balance'] -= payable

                order_num = f"CC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
                max_days = max((it['product'].get('delivery_days', 2) for it in summary['items']), default=2)
                est_deliv = (date.today() + timedelta(days=max_days)).strftime('%a, %d %b %Y')

                order_items = []
                for it in summary['items']:
                    order_items.append({
                        'product_id': it['product']['id'],
                        'title': it['product']['title'],
                        'image': it['product']['primary_image'],
                        'variant_label': it['variant_label'],
                        'unit_mrp': it['unit_mrp'],
                        'unit_price': it['unit_price'],
                        'quantity': it['quantity'],
                        'with_exchange': it['with_exchange'],
                        'exchange_discount': it['exchange_discount'],
                        'line_total': it['line_total'],
                    })
                    for prod in STORE.products:
                        if prod['id'] == it['product']['id']:
                            prod['stock'] = max(0, prod['stock'] - it['quantity'])
                            prod['sold_count'] += it['quantity']
                            break

                new_order = {
                    'order_number': order_num,
                    'created_at': datetime.now().strftime('%d %b %Y, %I:%M %p'),
                    'status': 'CONFIRMED',
                    'payment_method': payment_method,
                    'payment_status': 'PENDING' if payment_method == 'COD' else 'PAID',
                    'shipping_name': selected_addr['full_name'],
                    'shipping_phone': selected_addr['phone'],
                    'shipping_pincode': selected_addr['pincode'],
                    'shipping_address': f"{selected_addr['street_address']}, {selected_addr['locality']}",
                    'shipping_city': selected_addr['city'],
                    'shipping_state': selected_addr['state'],
                    'subtotal': summary['subtotal'],
                    'product_discount': summary['product_discount'],
                    'coupon_code': summary['coupon_code'],
                    'coupon_discount': summary['coupon_discount'],
                    'supercoins_used': summary['supercoins_used'],
                    'supercoins_discount': summary['supercoins_discount'],
                    'platform_fee': summary['platform_fee'],
                    'delivery_fee': summary['delivery_fee'],
                    'total_amount': payable,
                    'supercoins_earned': summary['coins_to_earn'],
                    'estimated_delivery': est_deliv,
                    'cancellation_reason': '',
                    'return_reason': '',
                    'items': order_items,
                }

                if summary['supercoins_used'] > 0:
                    account['supercoins'] = max(0, account['supercoins'] - summary['supercoins_used'])
                    account['coin_transactions'].insert(0, {
                        'amount': -summary['supercoins_used'],
                        'reason': f'Redeemed on Order #{order_num}',
                        'date': datetime.now().strftime('%d %b %Y'),
                    })

                account['supercoins'] += summary['coins_to_earn']
                account['coin_transactions'].insert(0, {
                    'amount': summary['coins_to_earn'],
                    'reason': f'Reward earned for Order #{order_num}',
                    'date': datetime.now().strftime('%d %b %Y'),
                })

                account['orders'].insert(0, new_order)
                account['notifications'].insert(0, {
                    'id': f'n-{uuid.uuid4().hex[:6]}',
                    'title': f'Order Confirmed: #{order_num}',
                    'message': f'Your order of ₹{payable:,} will arrive by {est_deliv}. You earned {summary["coins_to_earn"]} SuperCoins!',
                    'category': 'ORDER',
                    'link_url': f'/orders/{order_num}/',
                    'is_read': False,
                    'created_at': 'Just now',
                })

                account['cart'] = []
                account['applied_coupon'] = ''
                account['use_supercoins'] = False

                messages.success(request, f'Order #{order_num} placed successfully!')
                return redirect('order_detail', order_number=order_num)

    return render(request, 'landingpage/checkout.html', {
        'summary': summary,
        'addresses': account.get('addresses', []),
        'coupons': COUPONS,
    })


def orders_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        orders = copy.deepcopy(account.get('orders', []))

    q = (request.GET.get('q') or '').strip().lower()
    status_filter = (request.GET.get('status') or '').strip().upper()

    if q:
        orders = [
            o for o in orders
            if q in o['order_number'].lower() or any(q in it['title'].lower() for it in o['items'])
        ]
    if status_filter:
        orders = [o for o in orders if o['status'] == status_filter]

    return render(request, 'landingpage/orders.html', {
        'orders': orders,
        'q': q,
        'status_filter': status_filter,
    })


def order_detail(request, order_number):
    with STORE_LOCK:
        account = get_active_account(request)
        order = next((o for o in account.get('orders', []) if o['order_number'] == order_number), None)
        if not order:
            messages.error(request, 'Order not found.')
            return redirect('orders')

        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'advance_status' and order['status'] in ORDER_FLOW:
                idx = ORDER_FLOW.index(order['status'])
                if idx < len(ORDER_FLOW) - 1:
                    order['status'] = ORDER_FLOW[idx + 1]
                    if order['status'] == 'DELIVERED':
                        order['payment_status'] = 'PAID'
                        order['estimated_delivery'] = f"Delivered on {date.today().strftime('%d %b %Y')}"
                    account['notifications'].insert(0, {
                        'id': f'n-{uuid.uuid4().hex[:6]}',
                        'title': f"Order #{order['order_number']} is {order['status'].replace('_', ' ').title()}",
                        'message': 'Track your latest shipment status in My Orders.',
                        'category': 'ORDER',
                        'link_url': f"/orders/{order['order_number']}/",
                        'is_read': False,
                        'created_at': 'Just now',
                    })
                    messages.success(request, f"Order status updated to {order['status'].replace('_', ' ').title()}.")
            elif action == 'cancel_order' and order['status'] in ('PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED'):
                reason = (request.POST.get('reason') or 'Changed mind').strip()
                order['status'] = 'CANCELLED'
                order['cancellation_reason'] = reason
                if order['payment_status'] == 'PAID':
                    order['payment_status'] = 'REFUNDED'
                    account['wallet_balance'] += order['total_amount']
                messages.info(request, f"Order #{order['order_number']} cancelled. Any paid amount has been refunded to your Clickcart Wallet.")
            elif action == 'return_order' and order['status'] == 'DELIVERED':
                reason = (request.POST.get('reason') or 'Size / Quality issue').strip()
                order['status'] = 'RETURN_REQUESTED'
                order['return_reason'] = reason
                messages.success(request, 'Return pickup requested! Refund will be processed upon pickup.')
            return redirect('order_detail', order_number=order_number)

        order_copy = copy.deepcopy(order)
        step_idx = ORDER_FLOW.index(order_copy['status']) if order_copy['status'] in ORDER_FLOW else -1

    return render(request, 'landingpage/order_detail.html', {
        'order': order_copy,
        'step_idx': step_idx,
        'steps': [
            ('PLACED', 'Order Placed'),
            ('CONFIRMED', 'Confirmed'),
            ('PACKED', 'Packed'),
            ('SHIPPED', 'Shipped'),
            ('OUT_FOR_DELIVERY', 'Out for Delivery'),
            ('DELIVERED', 'Delivered'),
        ],
    })


def order_invoice(request, order_number):
    with STORE_LOCK:
        account = get_active_account(request)
        order = next((o for o in account.get('orders', []) if o['order_number'] == order_number), None)
        if not order:
            messages.error(request, 'Order invoice not found.')
            return redirect('orders')
        order_copy = copy.deepcopy(order)

    return render(request, 'landingpage/order_invoice.html', {'order': order_copy})


def login_view(request):
    if request.method == 'POST':
        demo_email = request.POST.get('demo_email')
        email = (demo_email or request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''

        with STORE_LOCK:
            user = STORE.users.get(email)
            if user and (demo_email or user['password'] == password):
                visitor_id = get_visitor_id(request)
                merge_guest_into_user(visitor_id, user)
                request.session['cc_user_email'] = email
                messages.success(request, f"Welcome back, {user['name']}!")
                return redirect(_safe_next(request, default='home'))
        messages.error(request, 'Invalid email or password. Try a Demo Account below!')
    return render(request, 'landingpage/login.html')


def signup_view(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        phone = (request.POST.get('phone') or '').strip()
        password = request.POST.get('password') or ''

        if not name or not email or not password:
            messages.error(request, 'Name, Email, and Password are required.')
            return render(request, 'landingpage/signup.html')

        with STORE_LOCK:
            if email in STORE.users:
                messages.error(request, 'An account with this email already exists. Please login.')
                return redirect('login')
            new_user = {
                'id': f'u-{uuid.uuid4().hex[:6]}',
                'name': name,
                'email': email,
                'password': password,
                'phone': phone,
                'gender': '',
                'is_plus_member': False,
                'is_seller': False,
                'store_name': '',
                'supercoins': 50,
                'wallet_balance': 2500,
                'addresses': [],
                'cart': [],
                'saved_for_later': [],
                'wishlist': [],
                'compare': [],
                'recently_viewed': [],
                'applied_coupon': '',
                'use_supercoins': False,
                'orders': [],
                'coin_transactions': [
                    {'amount': 50, 'reason': 'Welcome SuperCoins Gift', 'date': datetime.now().strftime('%d %b %Y')},
                ],
                'notifications': [
                    {
                        'id': f'n-{uuid.uuid4().hex[:6]}',
                        'title': 'Welcome to Clickcart!',
                        'message': 'You received ₹2,500 Demo Wallet balance and 50 SuperCoins!',
                        'category': 'COIN',
                        'link_url': '/supercoins/',
                        'is_read': False,
                        'created_at': 'Just now',
                    }
                ],
                'tickets': [],
            }
            STORE.users[email] = new_user
            visitor_id = get_visitor_id(request)
            merge_guest_into_user(visitor_id, new_user)
            request.session['cc_user_email'] = email

        messages.success(request, f'Account created! Welcome to Clickcart, {name}.')
        return redirect('home')
    return render(request, 'landingpage/signup.html')


def logout_view(request):
    request.session.pop('cc_user_email', None)
    messages.info(request, 'You have been signed out.')
    return redirect('home')


def account_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if not account.get('is_authenticated'):
            messages.info(request, 'Please sign in to manage your profile & saved addresses.')
            return redirect('login')

        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'update_profile':
                account['name'] = (request.POST.get('name') or account['name']).strip()
                account['phone'] = (request.POST.get('phone') or '').strip()
                account['gender'] = request.POST.get('gender', '')
                messages.success(request, 'Profile details updated.')
            elif action == 'add_address':
                full_name = (request.POST.get('full_name') or '').strip()
                phone = (request.POST.get('phone') or '').strip()
                pincode = (request.POST.get('pincode') or '').strip()
                street = (request.POST.get('street_address') or '').strip()
                city = (request.POST.get('city') or '').strip()
                state = (request.POST.get('state') or '').strip()
                if full_name and phone and pincode and street and city:
                    for a in account['addresses']:
                        a['is_default'] = False
                    account['addresses'].insert(0, {
                        'id': f'addr-{uuid.uuid4().hex[:6]}',
                        'full_name': full_name,
                        'phone': phone,
                        'pincode': pincode,
                        'locality': (request.POST.get('locality') or city).strip(),
                        'street_address': street,
                        'city': city,
                        'state': state or 'India',
                        'landmark': (request.POST.get('landmark') or '').strip(),
                        'address_type': request.POST.get('address_type', 'HOME'),
                        'is_default': True,
                    })
                    messages.success(request, 'New address added.')
            elif action == 'delete_address':
                aid = request.POST.get('address_id')
                account['addresses'] = [a for a in account['addresses'] if a['id'] != aid]
                messages.info(request, 'Address deleted.')
            elif action == 'set_default_address':
                aid = request.POST.get('address_id')
                for a in account['addresses']:
                    a['is_default'] = (a['id'] == aid)
                messages.success(request, 'Default delivery address updated.')
            elif action == 'topup_wallet':
                amt = int(request.POST.get('amount', 1000) or 1000)
                account['wallet_balance'] += max(100, min(50000, amt))
                messages.success(request, f'Added ₹{amt:,} to your Clickcart Wallet!')
            return redirect('account')

    return render(request, 'landingpage/account.html', {
        'addresses': account.get('addresses', []),
    })


def supercoins_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if request.method == 'POST':
            if not account.get('is_authenticated'):
                messages.info(request, 'Sign in first to redeem SuperCoins rewards.')
                return redirect('login')
            reward = request.POST.get('reward')
            if reward == 'voucher_500' and account['supercoins'] >= 50:
                account['supercoins'] -= 50
                account['wallet_balance'] += 150
                account['coin_transactions'].insert(0, {
                    'amount': -50,
                    'reason': 'Redeemed ₹150 Clickcart Wallet Gift Card',
                    'date': datetime.now().strftime('%d %b %Y'),
                })
                messages.success(request, '₹150 added to your Clickcart Wallet!')
            elif reward == 'plus_pass' and account['supercoins'] >= 100:
                account['supercoins'] -= 100
                account['is_plus_member'] = True
                account['coin_transactions'].insert(0, {
                    'amount': -100,
                    'reason': 'Activated Clickcart Plus Membership',
                    'date': datetime.now().strftime('%d %b %Y'),
                })
                messages.success(request, 'Clickcart Plus Membership unlocked!')
            else:
                messages.warning(request, 'Not enough SuperCoins for this reward.')
            return redirect('supercoins')

    return render(request, 'landingpage/supercoins.html', {
        'transactions': account.get('coin_transactions', []),
        'coupons': COUPONS,
    })


def plus_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if request.method == 'POST':
            if not account.get('is_authenticated'):
                messages.info(request, 'Sign in to activate Clickcart Plus Membership.')
                return redirect('login')
            account['is_plus_member'] = True
            account['notifications'].insert(0, {
                'id': f'n-{uuid.uuid4().hex[:6]}',
                'title': 'Welcome to Clickcart Plus!',
                'message': 'Free delivery on all orders + PLUS20 coupon (20% off) are now unlocked.',
                'category': 'COIN',
                'link_url': '/products/?deal=1',
                'is_read': False,
                'created_at': 'Just now',
            })
            messages.success(request, 'Clickcart Plus is now ACTIVE on your account!')
            return redirect('plus')

    return render(request, 'landingpage/plus.html', {
        'plus_coupons': [c for c in COUPONS if c['is_plus_only']],
    })


def seller_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'register_seller':
                if not account.get('is_authenticated'):
                    messages.info(request, 'Please sign in first to open your Clickcart Seller account.')
                    return redirect('login')
                store_name = (request.POST.get('store_name') or '').strip()
                if store_name:
                    account['is_seller'] = True
                    account['store_name'] = store_name
                    messages.success(request, f'Seller Hub activated for "{store_name}"!')
            elif action == 'add_product':
                title = (request.POST.get('title') or '').strip()
                brand = (request.POST.get('brand') or 'Clickcart Brand').strip()
                cat_slug = request.POST.get('category_slug', 'electronics')
                mrp = int(request.POST.get('mrp') or 1999)
                sp = int(request.POST.get('selling_price') or 1499)
                stock = int(request.POST.get('stock') or 25)
                short_desc = (request.POST.get('short_description') or '').strip() or 'Quality verified Clickcart marketplace product.'

                if title and cat_slug in CATEGORY_MAP:
                    pid = STORE.next_product_id
                    STORE.next_product_id += 1
                    cat_img_map = {
                        'mobiles': 'landingpage/images/prod-oneplus.svg',
                        'electronics': 'landingpage/images/prod-macbook.svg',
                        'appliances': 'landingpage/images/prod-tv.svg',
                        'fashion': 'landingpage/images/prod-nike.svg',
                        'beauty': 'landingpage/images/prod-serum.svg',
                        'home-furniture': 'landingpage/images/prod-chair.svg',
                        'grocery': 'landingpage/images/prod-grocery.svg',
                        'books-sports': 'landingpage/images/prod-book.svg',
                    }
                    new_prod = {
                        'id': pid,
                        'slug': f"{slugify(title)[:60]}-{pid}",
                        'sku': f'CC-SEL-{pid}',
                        'title': title,
                        'brand': brand,
                        'category_slug': cat_slug,
                        'category_name': CATEGORY_MAP[cat_slug]['name'],
                        'seller_name': account.get('store_name') or 'Clickcart Partner Store',
                        'seller_rating': 4.7,
                        'mrp': max(mrp, sp),
                        'selling_price': max(1, sp),
                        'stock': max(1, stock),
                        'is_assured': True,
                        'is_cod_available': True,
                        'is_exchange_available': False,
                        'max_exchange_discount': 0,
                        'warranty_summary': '1 Year Seller & Brand Warranty',
                        'return_policy_days': 7,
                        'delivery_days': 2,
                        'is_fast_delivery': True,
                        'is_deal_of_day': True,
                        'is_trending': True,
                        'primary_image': cat_img_map.get(cat_slug, 'landingpage/images/prod-sony-wh.svg'),
                        'gallery_images': [cat_img_map.get(cat_slug, 'landingpage/images/prod-sony-wh.svg')],
                        'short_description': short_desc,
                        'description': short_desc,
                        'highlights': [
                            f'Brand: {brand}',
                            'Clickcart Assured Quality Checked',
                            '7-Day Easy Replacement Policy',
                        ],
                        'specifications': {
                            'Brand': brand,
                            'Category': CATEGORY_MAP[cat_slug]['name'],
                            'Seller': account.get('store_name') or 'Clickcart Partner Store',
                        },
                        'variants': [
                            {'id': 1, 'variant_type': 'COLOR', 'name': 'Standard Edition', 'color_hex': '#2874F0', 'price_delta': 0, 'stock': max(1, stock)}
                        ],
                        'rating_avg': 4.8,
                        'rating_count': 1,
                        'sold_count': 0,
                        'reviews': [],
                        'questions': [],
                    }
                    STORE.products.insert(0, new_prod)
                    messages.success(request, f'"{title}" is now LIVE on Clickcart Marketplace!')
                    return redirect('product_detail', slug=new_prod['slug'])
            return redirect('seller')

        store_name = account.get('store_name') or 'SuperComNet Retail'
        seller_products = [enrich_product(copy.deepcopy(p)) for p in STORE.products if p['seller_name'] == store_name]
        if not seller_products:
            seller_products = get_all_products()[:6]

    return render(request, 'landingpage/seller.html', {
        'seller_products': seller_products,
        'categories': [c for c in CATEGORIES if c['slug'] != 'top-offers'],
        'store_name': store_name,
    })


def support_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if request.method == 'POST':
            topic = request.POST.get('topic', 'ORDER')
            order_num = (request.POST.get('order_number') or '').strip()
            subject = (request.POST.get('subject') or '').strip()
            message_body = (request.POST.get('message') or '').strip()
            if subject and message_body:
                tnum = f'TKT-{STORE.next_ticket_id}'
                STORE.next_ticket_id += 1
                account.setdefault('tickets', []).insert(0, {
                    'ticket_number': tnum,
                    'topic': topic,
                    'order_number': order_num,
                    'subject': subject,
                    'message': message_body,
                    'status': 'OPEN',
                    'reply': 'Our 24x7 Priority Resolution Team has received your ticket and will respond within 2 hours.',
                    'created_at': datetime.now().strftime('%d %b %Y, %I:%M %p'),
                })
                messages.success(request, f'Support ticket {tnum} created successfully!')
            else:
                messages.error(request, 'Please provide both Subject and Message.')
            return redirect('support')

    faqs = [
        ('How do I track my Clickcart order?', 'Go to My Orders from the top account menu and click any order to view live 5-step shipment tracking.'),
        ('How does SuperCoins redemption work?', 'Every order earns SuperCoins (2x for Plus members). Toggle "Redeem SuperCoins" inside your Shopping Cart to discount up to 10% off.'),
        ('What is Clickcart Assured?', 'Clickcart Assured guarantees 6-point quality check, genuine brand warranty, and super-fast delivery.'),
        ('How do cancellations & refunds work?', 'You can cancel any un-delivered order from Order Details. Prepaid & Wallet payments are refunded instantly to Clickcart Wallet.'),
    ]
    return render(request, 'landingpage/support.html', {
        'tickets': account.get('tickets', []),
        'orders': account.get('orders', []),
        'faqs': faqs,
    })


def notifications_view(request):
    with STORE_LOCK:
        account = get_active_account(request)
        if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
            for n in account.get('notifications', []):
                n['is_read'] = True
            messages.success(request, 'All notifications marked as read.')
            return redirect('notifications')
        notifs = copy.deepcopy(account.get('notifications', []))

    return render(request, 'landingpage/notifications.html', {'notifications': notifs})
