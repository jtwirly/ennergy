import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import pickle  # Replace joblib with pickle
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from meteostat import Point, Hourly, Daily
import pytz

class EnergyDashboard:
    def __init__(self):
        """Initialize dashboard with models and database connection"""
        self.database_path = "energy_data_NE.db"
        self.location = Point(42.3601, -71.0589)  # Boston coordinates for NE
        self.default_timezone = 'America/New_York'  # Default timezone for NE
        self.load_models()

    def load_models(self):
        """Load the pre-trained models"""
        try:
            self.models = {
                'solar': self.load_model('models/solar_model.pkl'),
                'wind': self.load_model('models/wind_model.pkl'),
                'demand': self.load_model('models/demand_model.pkl')
            }
            st.success("✅ Models loaded successfully")
        except Exception as e:
            st.error(f"Error loading models: {str(e)}")

    @staticmethod
    def load_model(filepath):
        """Load a model from a pickle file"""
        with open(filepath, 'rb') as file:
            return pickle.load(file)

    def get_available_dates(self):
        """Get range of available dates in the database"""
        conn = sqlite3.connect(self.database_path)
        query = """
        SELECT MIN(time) as min_date, MAX(time) as max_date
        FROM historical_weather_data
        """
        dates = pd.read_sql_query(query, conn)
        conn.close()

        min_date = pd.to_datetime(dates['min_date'][0])
        max_date = pd.to_datetime(dates['max_date'][0])

        return min_date, max_date

    def prepare_features(self, weather_data):
        """Prepare features for prediction"""
        features = weather_data[['temperature', 'dwpt', 'humidity', 'precipitation',
                               'wdir', 'windspeed', 'pres', 'cloudcover']]

        weather_data['hour'] = weather_data['datetime'].dt.hour
        weather_data['month'] = weather_data['datetime'].dt.month
        weather_data['season'] = np.where(weather_data['datetime'].dt.month.isin([12, 1, 2]), 1,
                                np.where(weather_data['datetime'].dt.month.isin([3, 4, 5]), 2,
                                np.where(weather_data['datetime'].dt.month.isin([6, 7, 8]), 3, 4)))
        weather_data['time_of_day'] = np.where(weather_data['datetime'].dt.hour < 6, 1,
                                      np.where(weather_data['datetime'].dt.hour < 12, 2,
                                      np.where(weather_data['datetime'].dt.hour < 18, 3, 4)))

        return pd.concat([features,
                         weather_data[['hour', 'month', 'season', 'time_of_day']]], axis=1)

    def get_meteostat_data(self, start_date):
        """Get weather data from Meteostat"""
        try:
            start = pd.to_datetime(start_date)
            end = start + timedelta(days=1)

            data = Hourly(self.location, start, end)
            data = data.fetch()

            data = data.rename(columns={
                'temp': 'temperature',
                'dwpt': 'dwpt',
                'rhum': 'humidity',
                'prcp': 'precipitation',
                'wdir': 'wdir',
                'wspd': 'windspeed',
                'pres': 'pres',
                'coco': 'cloudcover'
            })

            data = data.reset_index()
            data = data.rename(columns={'time': 'datetime'})

            return data

        except Exception as e:
            st.error(f"Error fetching Meteostat data: {str(e)}")
            return None

    def get_predictions(self, start_date):
        """Get predictions using Meteostat data"""
        pred_data = self.get_meteostat_data(start_date)

        if pred_data is None or pred_data.empty:
            return None

        pred_data['datetime'] = pd.to_datetime(pred_data['datetime'])
        X_pred = self.prepare_features(pred_data)

        predictions = {'datetime': pred_data['datetime']}
        for source, model in self.models.items():
            predictions[source] = model.predict(X_pred)

        return pd.DataFrame(predictions)

    def create_plots(self, predictions, overlay=False, timezone='UTC'):
        """Create interactive plots with option to overlay and timezone selection"""
        # Convert datetime to selected timezone
        predictions = predictions.copy()
        predictions['datetime'] = predictions['datetime'].dt.tz_localize('UTC').dt.tz_convert(timezone)

        if not overlay:
            # Original separate plots
            fig = make_subplots(
                rows=3,
                cols=1,
                subplot_titles=(
                    f'Energy Generation Forecast ({timezone})',
                    'Demand Forecast',
                    'Generation Mix'
                ),
                vertical_spacing=0.1,
                row_heights=[0.4, 0.3, 0.3]
            )

            # Generation predictions
            for source in ['solar', 'wind']:
                color = 'orange' if source == 'solar' else '#00B4D8'
                fig.add_trace(
                    go.Scatter(
                        x=predictions['datetime'],
                        y=predictions[source],
                        name=source.title(),
                        mode='lines+markers',
                        line=dict(color=color, width=2),
                        marker=dict(size=6)
                    ),
                    row=1,
                    col=1
                )

            # Demand prediction
            fig.add_trace(
                go.Scatter(
                    x=predictions['datetime'],
                    y=predictions['demand'],
                    name='Demand',
                    line=dict(color='#FF4B4B', width=2)
                ),
                row=2,
                col=1
            )

        else:
            # Overlaid plot
            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=(
                    f'Energy Generation and Demand Forecast ({timezone})',
                    'Generation Mix'
                ),
                vertical_spacing=0.2,
                row_heights=[0.7, 0.3]
            )

            # Generation and demand predictions (overlaid)
            for source in ['solar', 'wind', 'demand']:
                color = 'orange' if source == 'solar' else '#00B4D8' if source == 'wind' else '#FF4B4B'
                fig.add_trace(
                    go.Scatter(
                        x=predictions['datetime'],
                        y=predictions[source],
                        name=source.title(),
                        mode='lines+markers',
                        line=dict(color=color, width=2),
                        marker=dict(size=6)
                    ),
                    row=1,
                    col=1
                )

        # Generation mix (same for both views)
        total_gen = predictions['solar'] + predictions['wind']
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions['solar']/total_gen*100),
                name='Solar %',
                marker_color='#FFA62B'
            ),
            row=3 if not overlay else 2,
            col=1
        )
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions['wind']/total_gen*100),
                name='Wind %',
                marker_color='#00B4D8'
            ),
            row=3 if not overlay else 2,
            col=1
        )

        # Update layout for dark theme
        fig.update_layout(
            height=900,
            showlegend=True,
            barmode='stack',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            title=dict(
                text=f"Energy Generation and Demand Forecast ({timezone})",
                font=dict(size=24, color='white'),
                x=0.5
            )
        )

        # Update axes
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            title_text="Time",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )

        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )

        return fig
