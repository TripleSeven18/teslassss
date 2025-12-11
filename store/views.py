import decimal
import base64
import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import JsonResponse
import json
import uuid
from django.utils import timezone

from store.models import Address, Cart, Category, Order, OrderItem, Product
from .forms import AddressForm, RegistrationForm

# -----------------------------
# HOME + PRODUCT VIEWS
# -----------------------------
def home(request):
    categories = Category.objects.filter(is_active=True, is_featured=True)[:3]
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]

    return render(request, 'store/index.html', {
        'categories': categories,
        'products': products,
    })

def detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related = Product.objects.filter(
        is_active=True,
        category=product.category
    ).exclude(id=product.id)

    return render(request, 'store/detail.html', {
        'product': product,
        'related_products': related
    })

def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories': categories})

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)

    return render(request, 'store/category_products.html', {
        'category': category,
        'products': products,
        'categories': categories,
    })

# -----------------------------
# NEWSLETTER
# -----------------------------
def subscribe_newsletter(request):
    if request.method == 'POST':
        messages.success(request, "Thank you for subscribing to our newsletter!")
        return redirect(request.META.get('HTTP_REFERER', 'store:home'))
    return redirect('store:home')

# -----------------------------
# USER AUTHENTICATION
# -----------------------------
class RegistrationView(View):
    def get(self, request):
        return render(request, 'account/register.html', {
            'form': RegistrationForm()
        })

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Congratulations! Registration Successful!")
            return redirect('store:login')

        return render(request, 'account/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'account/profile.html', {
        'addresses': Address.objects.filter(user=request.user),
        'orders': Order.objects.filter(user=request.user),
    })

# -----------------------------
# USER ADDRESS MANAGEMENT
# -----------------------------
@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        return render(request, 'account/add_address.html', {
            'form': AddressForm()
        })

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            Address.objects.create(
                user=request.user,
                locality=form.cleaned_data['locality'],
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state']
            )
            messages.success(request, "New Address Added Successfully.")
            return redirect('store:profile')

        return render(request, 'account/add_address.html', {'form': form})

@login_required
def remove_address(request, id):
    address = get_object_or_404(Address, user=request.user, id=id)
    address.delete()
    messages.success(request, "Address removed successfully.")
    return redirect('store:profile')

# -----------------------------
# CART MANAGEMENT
# -----------------------------
@login_required
def add_to_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('prod_id')
        product = get_object_or_404(Product, id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    return redirect('store:cart')

@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(settings.SHIPPING_COST)

    for item in cart_products:
        amount += item.quantity * item.product.price

    total_amount = float(amount + shipping_amount)

    return render(request, 'store/cart.html', {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': total_amount,
        'addresses': Address.objects.filter(user=user),
    })

@login_required
def remove_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Product removed from cart.")
    return redirect('store:cart')

@login_required
def plus_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('store:cart')

@login_required
def minus_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)

    if cart_item.quantity <= 1:
        cart_item.delete()
    else:
        cart_item.quantity -= 1
        cart_item.save()

    return redirect('store:cart')

# -----------------------------
# CHECKOUT + ORDERS
# -----------------------------
@login_required
def checkout(request):
    address_id = request.GET.get('address')
    request.session['address_id'] = address_id
    return redirect('store:mpesa_payment')

# -----------------------------
# M-PESA PAYMENT
# -----------------------------
def get_access_token():
    try:
        api_url = f'{settings.MPESA_SANDBOX_URL}/oauth/v1/generate?grant_type=client_credentials'
        credentials = f'{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')

        headers = {
            'Authorization': f'Basic {encoded_credentials}'
        }

        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        if 'access_token' in response_data:
            return response_data['access_token']
        return None
    except requests.exceptions.RequestException as e:
        # Log the error
        print(f"Error getting access token: {e}")
        return None

@login_required
def mpesa_payment(request):
    user = request.user
    cart_items = Cart.objects.filter(user=user)

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('store:cart')

    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(settings.SHIPPING_COST)
    for item in cart_items:
        amount += item.quantity * item.product.price

    total_amount = amount + shipping_amount
    total_amount_int = int(total_amount)

    if request.method == 'POST':
        phone = request.POST.get('phone')
        
        # 1. Create Order
        address_id = request.session.get('address_id')
        if not address_id:
            messages.error(request, "Please select a shipping address.")
            return redirect('store:cart')
        
        address = get_object_or_404(Address, id=address_id)
        order_ref = str(uuid.uuid4())
        
        order = Order.objects.create(
            user=user,
            address=address,
            reference=order_ref,
            total_amount=total_amount,
            status='Pending'
        )
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        # 2. Get M-Pesa Access Token
        access_token = get_access_token()
        if not access_token:
            messages.error(request, "Could not connect to M-Pesa. Please try again later.")
            order.status = 'Failed'
            order.save()
            return redirect('store:payment_failed')

        # 3. Initiate STK Push
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_SHORTCODE_PASSWORD}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        url = f'{settings.MPESA_SANDBOX_URL}/mpesa/stkpush/v1/processrequest'
        callback_url = request.build_absolute_uri(reverse('store:mpesa_callback'))


        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": total_amount_int,
            "PartyA": phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": order_ref,
            "TransactionDesc": "Payment for goods"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('ResponseCode') == '0':
                messages.success(request, "STK push sent. Please complete the payment on your phone.")
                return redirect('store:orders')
            else:
                order.status = 'Failed'
                order.save()
                messages.error(request, response_data.get('errorMessage', 'An unknown error occurred.'))
                return redirect('store:payment_failed')

        except requests.exceptions.RequestException as e:
            print(f"Error during M-Pesa payment: {e}")
            order.status = 'Failed'
            order.save()
            messages.error(request, "An error occurred during payment. Please try again.")
            return redirect('store:payment_failed')

    return render(request, 'store/mpesa.html', {
        'cart_items': cart_items,
        'total_amount': total_amount
    })

# -----------------------------
# M-PESA CALLBACK VIEW
# -----------------------------
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("M-Pesa Callback Data:", data)

            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            
            if result_code == 0:
                # Payment successful
                checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
                # Find order by CheckoutRequestID if you store it, or use AccountReference
                # For now, let's assume AccountReference is reliable
                
                callback_metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
                
                account_ref = None
                # This is a simplified way to get the AccountReference. 
                # A more robust solution would be to iterate through the list and check the 'Name'
                if len(callback_metadata) > 3:
                    account_ref = callback_metadata[4]['Value']

                
                if account_ref:
                    try:
                        order = Order.objects.get(reference=account_ref)
                        order.status = 'Paid'
                        order.save()
                        
                        # Clear the cart
                        Cart.objects.filter(user=order.user).delete()
                        
                        return JsonResponse({'status': 'success', 'message': 'Payment completed successfully.'})
                    except Order.DoesNotExist:
                        print(f"Order with reference {account_ref} not found.")
                        return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
                else:
                    return JsonResponse({'status': 'error', 'message': 'AccountReference not found in callback.'}, status=400)

            else:
                # Payment failed or was cancelled
                error_message = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
                checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
                
                # Find and update order status to 'Failed'
                # Again, assuming AccountReference is available
                
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            print(f"Error processing M-Pesa callback: {e}")
            return JsonResponse({'status': 'error', 'message': 'An internal server error occurred.'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def orders(request):
    order_list = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': order_list})

# -----------------------------
# STATIC PAGES
# -----------------------------
def shop(request):
    return render(request, 'store/shop.html')

def test(request):
    return render(request, 'store/test.html')

def payment_success(request):
    return render(request, 'store/payment_success.html')

def payment_failed(request):
    return render(request, 'store/payment_failed.html')
