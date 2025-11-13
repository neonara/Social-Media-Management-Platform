"""
ML Model training and prediction service for engagement forecasting.
Trains on synthetic/real data and provides predictions for posts.
"""

import pickle
import os
from pathlib import Path
import logging
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from apps.ai_integration.models import TrainingData, ModelMetrics

logger = logging.getLogger(__name__)


class EngagementForecastModel:
    """
    ML model for predicting post engagement before publishing.
    Supports training with synthetic and real data.
    """
    
    MODEL_DIR = Path(__file__).resolve().parent.parent.parent / 'ml_models'
    
    def __init__(self, model_type='random_forest'):
        """
        Initialize the model.
        
        Args:
            model_type: 'random_forest' or 'linear_regression'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = [
            'caption_length',
            'hashtag_count',
            'time_of_day',
            'day_of_week',
            'platform_facebook',
            'platform_instagram',
            'platform_linkedin',
            'media_type_image',
            'media_type_video',
            'media_type_carousel',
            'media_type_text',
            'brand_sentiment'
        ]
        
        # Create model directory if it doesn't exist
        self.MODEL_DIR.mkdir(exist_ok=True)
        
        self._load_model()
    
    def _encode_features(self, data_list):
        """
        Convert raw features to one-hot encoded format.
        
        Args:
            data_list: List of dicts with raw features
        
        Returns:
            numpy array of shape (n_samples, n_features)
        """
        encoded = []
        
        for data in data_list:
            features = [
                data['caption_length'],
                data['hashtag_count'],
                data['time_of_day'],
                data['day_of_week'],
                1 if data['platform'] == 'facebook' else 0,
                1 if data['platform'] == 'instagram' else 0,
                1 if data['platform'] == 'linkedin' else 0,
                1 if data['media_type'] == 'image' else 0,
                1 if data['media_type'] == 'video' else 0,
                1 if data['media_type'] == 'carousel' else 0,
                1 if data['media_type'] == 'text' else 0,
                data['brand_sentiment'],
            ]
            encoded.append(features)
        
        return np.array(encoded)
    
    def train(self, data_type='synthetic'):
        """
        Train the model on synthetic or real data.
        
        Args:
            data_type: 'synthetic', 'real', or 'combined'
        
        Returns:
            dict with training metrics
        """
        logger.info(f"Starting model training with data_type={data_type}")
        
        # Fetch training data
        if data_type == 'combined':
            query = TrainingData.objects.all()
        else:
            query = TrainingData.objects.filter(data_type=data_type)
        
        if not query.exists():
            logger.error(f"No training data found for data_type={data_type}")
            raise ValueError(f"No training data found for data_type={data_type}")
        
        # Prepare data
        training_records = list(query.values())
        data_list = [
            {
                'caption_length': r['caption_length'],
                'hashtag_count': r['hashtag_count'],
                'time_of_day': r['time_of_day'],
                'day_of_week': r['day_of_week'],
                'platform': r['platform'],
                'media_type': r['media_type'],
                'brand_sentiment': r['brand_sentiment'],
            }
            for r in training_records
        ]
        engagement_scores = np.array([r['engagement_score'] for r in training_records])
        
        X = self._encode_features(data_list)
        y = engagement_scores
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        if self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        else:
            self.model = LinearRegression()
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"Model training complete: R²={r2:.4f}, MAE={mae:.2f}, RMSE={rmse:.2f}")
        
        # Save model
        self._save_model()
        
        # Save metrics
        version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        metrics = ModelMetrics.objects.create(
            version=version,
            model_type=self.model_type,
            training_samples=len(training_records),
            r2_score=r2,
            mae=mae,
            rmse=rmse,
            training_data_type=data_type,
            is_active=True
        )
        
        logger.info(f"Model metrics saved: {metrics.version}")
        
        return {
            'r2_score': r2,
            'mae': mae,
            'rmse': rmse,
            'training_samples': len(training_records),
            'model_version': version
        }
    
    def predict(self, post_data):
        """
        Predict engagement for a post.
        
        Args:
            post_data: dict with keys:
                - caption_length
                - hashtag_count
                - time_of_day
                - day_of_week
                - platform
                - media_type
                - brand_sentiment
        
        Returns:
            dict with prediction and confidence
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X = self._encode_features([post_data])
        X_scaled = self.scaler.transform(X)
        
        prediction = self.model.predict(X_scaled)[0]
        
        # Get confidence (for Random Forest)
        if self.model_type == 'random_forest':
            # Get predictions from all trees to estimate confidence
            predictions = np.array([
                tree.predict(X_scaled)[0] for tree in self.model.estimators_
            ])
            confidence = 1.0 - (np.std(predictions) / (max(predictions) - min(predictions) + 1e-8))
            confidence = max(0, min(1, confidence))
        else:
            # Linear regression - confidence based on R²
            active_model = ModelMetrics.objects.filter(is_active=True).first()
            confidence = active_model.r2_score if active_model else 0.7
        
        # Clamp prediction to 0-100
        prediction = max(0, min(100, prediction))
        
        # Determine engagement level
        if prediction < 33:
            level = 'low'
        elif prediction < 66:
            level = 'medium'
        else:
            level = 'high'
        
        return {
            'predicted_engagement_score': float(prediction),
            'engagement_level': level,
            'confidence_score': float(confidence)
        }
    
    def get_feature_importance(self):
        """
        Get feature importance for Random Forest model.
        
        Returns:
            dict mapping feature names to importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained.")
        
        if self.model_type != 'random_forest':
            logger.warning("Feature importance only available for Random Forest model")
            return {}
        
        importances = self.model.feature_importances_
        importance_dict = dict(zip(self.feature_names, importances))
        
        # Sort by importance
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    
    def _save_model(self):
        """Save model and scaler to disk"""
        model_path = self.MODEL_DIR / f'model_{self.model_type}.pkl'
        scaler_path = self.MODEL_DIR / 'scaler.pkl'
        
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Model saved to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load model and scaler from disk if available"""
        model_path = self.MODEL_DIR / f'model_{self.model_type}.pkl'
        scaler_path = self.MODEL_DIR / 'scaler.pkl'
        
        try:
            if model_path.exists() and scaler_path.exists():
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info(f"Model loaded from {model_path}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
