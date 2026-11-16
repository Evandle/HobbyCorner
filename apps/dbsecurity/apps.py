from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DbSecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dbsecurity"
    label = "dbsecurity"

    def ready(self):
        from .rls import enable_rls_after_migrate

        # sender=self: the signal goes out once per app, so listening to our own
        # app means the hook runs once per `migrate`, after all migrations are done.
        post_migrate.connect(
            enable_rls_after_migrate, sender=self, dispatch_uid="dbsecurity.enable_rls"
        )
