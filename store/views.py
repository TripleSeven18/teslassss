import decimal
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from store.models import Address, Cart, Category, Order, Product
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
        # In a real application, you would handle the subscription here
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

    return render(request, 'store/cart.html', {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
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
    user = request.user
    address_id = request.GET.get('address')
    
    # Storing address_id in session
    request.session['address_id'] = address_id
    
    # Redirect to M-Pesa payment page
    return redirect('store:mpesa_payment')


@login_required
def mpesa_payment(request):
    user = request.user
    cart_items = Cart.objects.filter(user=user)
    
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(settings.SHIPPING_COST)
    for item in cart_items:
        amount += item.quantity * item.product.price
    total_amount = amount + shipping_amount

    if request.method == 'POST':
        phone = request.POST.get('phone')
        # Here you would add the M-Pesa API call
        # For now, we'll just simulate a successful payment
        
        address_id = request.session.get('address_id')
        if not address_id:
            messages.error(request, "No shipping address selected.")
            return redirect('store:cart')

        address = get_object_or_404(Address, id=address_id, user=user)

        for item in cart_items:
            Order.objects.create(
                user=user,
                address=address,
                product=item.product,
                quantity=item.quantity
            )
            item.delete()
        
        messages.success(request, "Your order has been placed successfully!")
        return redirect('store:orders')

    # Storing address_id in session
    address_id = request.GET.get('address')
    if address_id:
        request.session['address_id'] = address_id

    return render(request, 'store/mpesa.html', {
        'cart_items': cart_items,
        'total_amount': total_amount
    })


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
