"""
Management command to train the ML engagement forecast model.
"""

from django.core.management.base import BaseCommand
from apps.ai_integration.services.ml_service import EngagementForecastModel


class Command(BaseCommand):
    help = 'Train the ML engagement forecast model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-type',
            type=str,
            default='random_forest',
            choices=['random_forest', 'linear_regression'],
            help='Type of ML model to train (default: random_forest)'
        )
        parser.add_argument(
            '--data-type',
            type=str,
            default='synthetic',
            choices=['synthetic', 'real', 'combined'],
            help='Type of data to train on (default: synthetic)'
        )

    def handle(self, *args, **options):
        model_type = options['model_type']
        data_type = options['data_type']

        self.stdout.write(self.style.WARNING(f'\n🤖 Training {model_type} model on {data_type} data...\n'))

        try:
            model = EngagementForecastModel(model_type=model_type)
            metrics = model.train(data_type=data_type)

            self.stdout.write(self.style.SUCCESS('\n✓ Model training completed successfully!\n'))
            self.stdout.write(self.style.SUCCESS('📊 Training Metrics:\n'))
            self.stdout.write(f'   • R² Score: {metrics["r2_score"]:.4f}')
            self.stdout.write(f'   • Mean Absolute Error: {metrics["mae"]:.2f}')
            self.stdout.write(f'   • Root Mean Squared Error: {metrics["rmse"]:.2f}')
            self.stdout.write(f'   • Training Samples: {metrics["training_samples"]}')
            self.stdout.write(f'   • Model Version: {metrics["model_version"]}')

            # Display feature importance if available
            if model_type == 'random_forest':
                self.stdout.write(self.style.SUCCESS('\n🔥 Top 5 Important Features:\n'))
                importance = model.get_feature_importance()
                for i, (feature, importance_score) in enumerate(list(importance.items())[:5], 1):
                    self.stdout.write(f'   {i}. {feature}: {importance_score:.4f}')

            self.stdout.write(self.style.SUCCESS('\n✓ Model ready for predictions!\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error during training: {str(e)}\n'))
