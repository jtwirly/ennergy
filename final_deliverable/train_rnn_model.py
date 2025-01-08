# hierarchical_rnn_model.py

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
from sklearn.preprocessing import MinMaxScaler

class TimeSeriesEncoder(nn.Module):
    def __init__(self, input_size: int, hidden_size: int):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True,
            bidirectional=True
        )

    def forward(self, x):
        output, (hidden, cell) = self.lstm(x)
        return torch.cat((hidden[-2], hidden[-1]), dim=0)

class HierarchicalEnergyForecaster(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        forecast_horizons: List[int] = [24, 168, 720]  # 24h, 1w, 30d
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.forecast_horizons = forecast_horizons
        
        # Encoders
        self.short_term_encoder = TimeSeriesEncoder(input_size, hidden_size)
        self.medium_term_encoder = TimeSeriesEncoder(input_size, hidden_size)
        self.long_term_encoder = TimeSeriesEncoder(input_size, hidden_size)
        
        combined_size = hidden_size * 2 * 3
        
        # Prediction heads
        self.prediction_heads = self._create_prediction_heads(combined_size)
        
        # Initialize scalers
        self.scalers = self._initialize_scalers()

    def _create_prediction_heads(self, combined_size):
        return nn.ModuleDict({
            source: nn.ModuleDict({
                str(horizon): self._create_head(combined_size, horizon)
                for horizon in self.forecast_horizons
            })
            for source in ['solar', 'wind', 'demand']
        })

    def _create_head(self, input_size, output_size):
        return nn.Sequential(
            nn.Linear(input_size, self.hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(self.hidden_size, output_size)
        )

    def _initialize_scalers(self):
        return {
            'features': MinMaxScaler(),
            'solar': MinMaxScaler(),
            'wind': MinMaxScaler(),
            'demand': MinMaxScaler()
        }
    
    def forward(self, x_dict: Dict[str, torch.Tensor]) -> Dict[str, Dict[str, torch.Tensor]]:
        # Process each time scale
        short_term_features = self.short_term_encoder(x_dict['short_term'])
        medium_term_features = self.medium_term_encoder(x_dict['medium_term'])
        long_term_features = self.long_term_encoder(x_dict['long_term'])
        
        # Combine features
        combined = torch.cat([
            short_term_features,
            medium_term_features,
            long_term_features
        ], dim=0)
        
        # Generate predictions for each source and horizon
        predictions = {
            source: {
                str(horizon): head(combined)
                for horizon, head in heads.items()
            }
            for source, heads in self.prediction_heads.items()
        }
        
        return predictions

    def prepare_data(self, weather_data: pd.DataFrame, energy_data: Dict[str, pd.DataFrame]) -> Tuple:
        """Prepare data for training with multiple time horizons"""
        # Scale features
        features = weather_data[[
            'temperature', 'dwpt', 'humidity', 'precipitation',
            'wdir', 'windspeed', 'pres', 'cloudcover'
        ]]
        
        # Add temporal features
        weather_data['hour'] = weather_data['datetime'].dt.hour
        weather_data['month'] = weather_data['datetime'].dt.month
        weather_data['season'] = weather_data['datetime'].dt.month.map(
            lambda m: 1 if m in [12, 1, 2] else 2 if m in [3, 4, 5] else 3 if m in [6, 7, 8] else 4
        )
        weather_data['time_of_day'] = weather_data['datetime'].dt.hour.map(
            lambda h: 1 if h < 6 else 2 if h < 12 else 3 if h < 18 else 4
        )
        
        all_features = pd.concat([
            features,
            weather_data[['hour', 'month', 'season', 'time_of_day']]
        ], axis=1)
        
        scaled_features = self.scalers['features'].fit_transform(all_features)
        
        # Prepare sequences for different time horizons
        sequences = {
            'short_term': self._create_sequences(scaled_features, 24),
            'medium_term': self._create_sequences(scaled_features, 168),
            'long_term': self._create_sequences(scaled_features, 720)
        }
        
        # Scale and prepare targets
        targets = {}
        for source, data in energy_data.items():
            scaled_values = self.scalers[source].fit_transform(data[['value']])
            targets[source] = {
                str(horizon): scaled_values[horizon:] 
                for horizon in self.forecast_horizons
            }
        
        return sequences, targets
    
    def _create_sequences(self, data: np.ndarray, sequence_length: int) -> torch.Tensor:
        """Create sequences for a specific time horizon"""
        sequences = []
        for i in range(len(data) - sequence_length):
            sequences.append(data[i:(i + sequence_length)])
        return torch.FloatTensor(np.array(sequences))
    
    def predict(self, weather_data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Make predictions compatible with the existing interface"""
        self.eval()
        with torch.no_grad():
            # Prepare features
            features = self.prepare_data(weather_data, {})[0]
            
            # Get predictions
            predictions = self(features)
            
            # Convert predictions back to original scale
            return {
                source: {
                    horizon: self.scalers[source].inverse_transform(pred.numpy())
                    for horizon, pred in horizons.items()
                }
                for source, horizons in predictions.items()
            }