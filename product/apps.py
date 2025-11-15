from django.apps import AppConfig


class ProductApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'product'

    def ready(self):
        from . import signals
