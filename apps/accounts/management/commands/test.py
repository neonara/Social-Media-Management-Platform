from django.core.management.commands.test import Command as BaseTestCommand


class Command(BaseTestCommand):
    """
    Custom test command that automatically runs all app tests with verbosity 2 by default
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Override the default verbosity to 2
        parser.set_defaults(verbosity=2)

    def handle(self, *test_labels, **options):
        # If no test labels provided, run all app tests
        if not test_labels:
            test_labels = (
                'apps.accounts.tests',
                'apps.content.tests',
                'apps.ai_integration.tests',
                'apps.notifications.tests',
                'apps.collaboration.tests',
                'apps.social_media.tests',
            )
        
        # Call the parent command with our test labels
        super().handle(*test_labels, **options)
