from django.core.management.base import BaseCommand

from core import maintenance


class Command(BaseCommand):
    help = "Resend failed notifications, delete old closed requests, back up database + uploads."

    def add_arguments(self, parser):
        parser.add_argument("--retry", action="store_true", help="only resend failed notifications")
        parser.add_argument("--backup", action="store_true", help="only make a backup")
        parser.add_argument("--purge", action="store_true", help="only delete old closed requests")

    def handle(self, *args, **o):
        only = o["retry"] or o["backup"] or o["purge"]
        if o["retry"] or not only:
            sent, failed = maintenance.retry_notifications()
            self.stdout.write(f"Notifications resent: {sent}, still failing: {failed}")
        if o["purge"] or not only:
            orders, consults = maintenance.purge_old()
            self.stdout.write(f"Deleted old orders: {orders}, consultations: {consults}")
        if o["backup"] or not only:
            path = maintenance.backup()
            self.stdout.write(self.style.SUCCESS(f"Backup: {path}"))
