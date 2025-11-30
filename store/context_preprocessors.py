from .models import Category, Cart


def store_menu(request):
    """Provide active categories to all templates."""
    return {
        'categories_menu': Category.objects.filter(is_active=True)
    }


def cart_menu(request):
    """Provide cart items for authenticated users."""
    if request.user.is_authenticated:
        return {
            'cart_items': Cart.objects.filter(user=request.user)
        }
    return {}


def currency(request):
    """Provide global currency symbol."""
    return {
        'CURRENCY_SYMBOL': "KSH"
    }
