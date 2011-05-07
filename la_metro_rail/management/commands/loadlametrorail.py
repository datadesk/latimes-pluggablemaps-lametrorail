from django.core.management.base import BaseCommand, CommandError
from la_metro_rail import load

class Command(BaseCommand):
    help = 'Loads data for pluggable maps of L.A. Metro Rail lines'

    def handle(self, *args, **options):
        print 'Loading data for L.A. Metro Rail lines'
        load.all()
        print 'Successfully loaded data'
