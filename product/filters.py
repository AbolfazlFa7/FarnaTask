from django_filters import rest_framework as filters
from .models import (
    Category, Product, ProductImage, ProductAttribute,
    Coupon, CategoryCoupon, ProductCoupon, Review, ReviewImage,
    CartItem, Order, OrderItem, Payment
)


class ProductListFilter(filters.FilterSet):
    tags = filters.CharFilter(method='filter_by_tags')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    category = filters.CharFilter(
        field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = {
            'price': ['exact', 'gt', 'lt', 'gte', 'lte'],
            'stock': ['exact', 'gt', 'lt', 'gte', 'lte'],
        }

    def filter_by_tags(self, queryset, name, value):
        return queryset.filter(tags__name__in=value.split(',')).distinct()
