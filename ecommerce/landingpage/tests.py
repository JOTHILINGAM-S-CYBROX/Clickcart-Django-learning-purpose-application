import os
from django.conf import settings
from django.test import Client, SimpleTestCase


class ClickcartFeatureTests(SimpleTestCase):
    """End-to-end tests for DB-free Clickcart Flipkart-featured e-commerce site."""

    def setUp(self):
        self.client = Client(HTTP_HOST='localhost')

    def test_pages_and_catalog_filters(self):
        for url in [
            '/',
            '/products/',
            '/products/?category=mobiles',
            '/products/?q=iphone&sort=price_asc',
            '/products/?min_price=1000&max_price=60000&min_rating=4&assured=1',
            '/product/apple-iphone-16-pro-128gb/',
            '/cart/',
            '/wishlist/',
            '/compare/',
            '/login/',
            '/signup/',
            '/supercoins/',
            '/plus/',
            '/seller/',
            '/support/',
            '/notifications/',
        ]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f'Failed GET {url}')

    def test_search_suggest_and_pincode_apis(self):
        s_resp = self.client.get('/api/search-suggest/?q=iphone')
        self.assertEqual(s_resp.status_code, 200)
        self.assertTrue(len(s_resp.json()['suggestions']) >= 1)

        p_resp = self.client.get('/api/check-pincode/?ajax=1&pincode=641001')
        self.assertEqual(p_resp.status_code, 200)
        self.assertEqual(p_resp.json()['data']['city'], 'Coimbatore')

        bad_p = self.client.get('/api/check-pincode/?ajax=1&pincode=999999')
        self.assertEqual(bad_p.status_code, 400)

    def test_full_shopping_cart_coupon_checkout_and_orders(self):
        # 1. Demo login
        login_resp = self.client.post('/login/', {'demo_email': 'aarav@clickcart.in'}, follow=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertContains(login_resp, 'Aarav Sharma')

        # 2. Wishlist & Compare toggles
        w_resp = self.client.get('/wishlist/toggle/2/?ajax=1')
        self.assertEqual(w_resp.status_code, 200)
        self.assertTrue(w_resp.json()['ok'])

        c_resp = self.client.get('/compare/toggle/1/?ajax=1')
        self.assertEqual(c_resp.status_code, 200)
        self.assertTrue(c_resp.json()['added'])

        # 3. Add product to cart and apply coupon
        self.client.post('/cart/add/3/', {'quantity': 1, 'redirect_to': 'cart'})
        cart_resp = self.client.get('/cart/')
        self.assertContains(cart_resp, 'OnePlus 13R 5G')

        self.client.post('/cart/coupon/', {'action': 'apply', 'code': 'SAVE10'})
        cart_after = self.client.get('/cart/')
        self.assertContains(cart_after, 'Coupon (SAVE10)')

        # 4. Checkout and place order
        co_resp = self.client.post('/checkout/', {
            'action': 'place_order',
            'selected_address_id': 'addr-1',
            'payment_method': 'UPI',
        }, follow=True)
        self.assertEqual(co_resp.status_code, 200)
        self.assertContains(co_resp, 'placed successfully')
        self.assertContains(co_resp, 'Order Placed')

    def test_seller_live_listing_and_support_ticket(self):
        self.client.post('/login/', {'demo_email': 'seller@clickcart.in'})
        sel_resp = self.client.post('/seller/', {
            'action': 'add_product',
            'title': 'Clickcart Test Earbuds Pro',
            'brand': 'boAt',
            'category_slug': 'electronics',
            'mrp': 2999,
            'selling_price': 1299,
            'stock': 20,
            'short_description': 'Active noise cancellation earbuds.',
        }, follow=True)
        self.assertEqual(sel_resp.status_code, 200)
        self.assertContains(sel_resp, 'Clickcart Test Earbuds Pro')

        sup_resp = self.client.post('/support/', {
            'topic': 'ORDER',
            'subject': 'Delivery slot change',
            'message': 'Please deliver after 5 PM.',
        }, follow=True)
        self.assertEqual(sup_resp.status_code, 200)
        self.assertContains(sup_resp, 'Delivery slot change')

    def test_database_remains_unused(self):
        db_path = settings.BASE_DIR / 'db.sqlite3'
        if os.path.exists(db_path):
            self.assertEqual(os.path.getsize(db_path), 0)
