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
        """Load the pre-trained hierarchical RNN model"""
        try:
            self.model = HierarchicalEnergyForecaster(input_size=12)
            self.model.load_state_dict(torch.load('hierarchical_rnn_model.pkl'))
            self.model.eval()
            st.success("✅ Model loaded successfully")
        except Exception as e:
            st.error(f"Error loading model: {str(e)}")

    @staticmethod
    def load_model(filepath):
        """Load a model from a pickle file"""
        with open(filepath, 'rb') as file:
            return pickle.load(file)

    def get_available_dates(self):
        """Get range of available dates in the database"""
        # conn = sqlite3.connect(self.database_path)
        # query = """
        # SELECT MIN(time) as min_date, MAX(time) as max_date
        # FROM historical_weather_data
        # """
        # dates = pd.read_sql_query(query, conn)
            # conn.close()
        min_date = pd.to_datetime('2022-10-27 00:00:00')
        max_date = pd.to_datetime('2024-10-27 00:00:00')
        print(f"{max_date}")
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
    """Get predictions using hierarchical RNN model"""
    pred_data = self.get_meteostat_data(start_date)

    if pred_data is None or pred_data.empty:
        return None

    pred_data['datetime'] = pd.to_datetime(pred_data['datetime'])
    
    # Get predictions
    predictions = self.model.predict(pred_data)
    
    # Create DataFrame with predictions
    results = pd.DataFrame({
        'datetime': pred_data['datetime'],
        'solar_24h': predictions['solar']['24'],
        'solar_1w': predictions['solar']['168'],
        'solar_30d': predictions['solar']['720'],
        'wind_24h': predictions['wind']['24'],
        'wind_1w': predictions['wind']['168'],
        'wind_30d': predictions['wind']['720'],
        'demand_24h': predictions['demand']['24'],
        'demand_1w': predictions['demand']['168'],
        'demand_30d': predictions['demand']['720']
    })
    
    return results

def create_plots(self, predictions, overlay=False, timezone='UTC', horizon='24h'):
    """Enhanced plots with multiple time horizons"""
    predictions = predictions.copy()
    predictions['datetime'] = predictions['datetime'].dt.tz_localize('UTC').dt.tz_convert(timezone)
    
    # Select columns for the chosen horizon
    solar_col = f'solar_{horizon}'
    wind_col = f'wind_{horizon}'
    demand_col = f'demand_{horizon}'
    
    if not overlay:
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=(
                f'Energy Generation Forecast - {horizon} ({timezone})',
                'Demand Forecast',
                'Generation Mix',
                'Forecast Comparison'
            ),
            vertical_spacing=0.1,
            row_heights=[0.3, 0.2, 0.2, 0.3]
        )
        
        # Generation predictions
        for source, col in [('Solar', solar_col), ('Wind', wind_col)]:
            color = 'orange' if source == 'Solar' else '#00B4D8'
            fig.add_trace(
                go.Scatter(
                    x=predictions['datetime'],
                    y=predictions[col],
                    name=f'{source} ({horizon})',
                    mode='lines+markers',
                    line=dict(color=color, width=2),
                    marker=dict(size=6)
                ),
                row=1, col=1
            )
        
        # Demand prediction
        fig.add_trace(
            go.Scatter(
                x=predictions['datetime'],
                y=predictions[demand_col],
                name=f'Demand ({horizon})',
                line=dict(color='#FF4B4B', width=2)
            ),
            row=2, col=1
        )
        
        # Generation mix
        total_gen = predictions[solar_col] + predictions[wind_col]
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions[solar_col]/total_gen*100),
                name='Solar %',
                marker_color='#FFA62B'
            ),
            row=3, col=1
        )
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions[wind_col]/total_gen*100),
                name='Wind %',
                marker_color='#00B4D8'
            ),
            row=3, col=1
        )
        
        # Forecast comparison across horizons
        for h in ['24h', '1w', '30d']:
            fig.add_trace(
                go.Scatter(
                    x=predictions['datetime'],
                    y=predictions[f'solar_{h}'],
                    name=f'Solar ({h})',
                    line=dict(dash='dot' if h != horizon else 'solid')
                ),
                row=4, col=1
            )
    
    # Update layout
    fig.update_layout(
        height=1200,
        showlegend=True,
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text=f"Hierarchical Energy Forecast ({timezone})",
            font=dict(size=24, color='white'),
            x=0.5
        )
    )
    
    return fig


def main():
    st.set_page_config(page_title="Energy Generation Forecast", layout="wide")

    st.title("⚡ Energy Generation Forecast Dashboard")

    # Initialize dashboard
    dashboard = EnergyDashboard()

    # Get available date range (from your database for historical validation)
    min_date, max_date = dashboard.get_available_dates()

    # Extend max_date to allow for future predictions
    extended_max_date = datetime.now() + timedelta(days=7)

    # Sidebar
    st.sidebar.header("Forecast Settings")

    # Timezone selection
    timezone_options = {
        'NE (Eastern Time)': 'America/New_York',
        'UTC': 'UTC'
    }
    selected_timezone = st.sidebar.selectbox(
        'Select Timezone',
        options=list(timezone_options.keys()),
        index=0
    )
    timezone = timezone_options[selected_timezone]

    # Show available date range
    st.sidebar.info(f"""
        Data range:
        - Historical data: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}
        - Predictions available up to: {extended_max_date.strftime('%Y-%m-%d')}

        Note: Future predictions use Meteostat weather data
    """)

    # Date selection with extended range
    selected_date = st.sidebar.date_input(
        "Select forecast date",
        min_value=min_date.date(),
        max_value=extended_max_date.date(),
        value=datetime.now().date()
    )

    # Time selection
    selected_time = st.sidebar.time_input(
        "Select start time",
        value=datetime.strptime('00:00', '%H:%M').time()
    )

    # Combine date and time
    start_datetime = datetime.combine(selected_date, selected_time)

    # Add warning for future dates
    if start_datetime.date() > datetime.now().date():
        st.sidebar.warning("⚠️ Showing predictions using Meteostat forecast data")
    elif start_datetime.date() < min_date.date():
        st.error(f"Selected date is before available historical data ({min_date.strftime('%Y-%m-%d')})")
        return

    # Get predictions
    with st.spinner('Generating predictions...'):
        predictions = dashboard.get_predictions(start_datetime)

        if predictions is None or predictions.empty:
            st.error(f"""
                No data available for {start_datetime.strftime('%Y-%m-%d %H:%M')}.
                This might be because:
                1. No weather data available from Meteostat
                2. Error in data retrieval

                Try selecting a different date or check Meteostat service status.
            """)
            return

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Forecasts", "📊 Statistics", "ℹ️ Info"])

    with tab1:
        overlay_plots = st.checkbox("Overlay Generation and Demand", value=False)

        # Display plots with timezone support
        st.plotly_chart(dashboard.create_plots(predictions, overlay=overlay_plots, timezone=timezone),
                       use_container_width=True)

        # Display raw data if requested
        if st.checkbox("Show raw data"):
            # Convert datetime to selected timezone for display
            display_predictions = predictions.copy()
            display_predictions['datetime'] = display_predictions['datetime'].dt.tz_localize('UTC').dt.tz_convert(timezone)
            st.dataframe(display_predictions)

    with tab2:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Peak Solar Generation",
                f"{predictions['solar'].max():.1f} MWh",
                f"{predictions['solar'].mean():.1f} MWh avg"
            )

        with col2:
            st.metric(
                "Peak Wind Generation",
                f"{predictions['wind'].max():.1f} MWh",
                f"{predictions['wind'].mean():.1f} MWh avg"
            )

        with col3:
            st.metric(
                "Peak Demand",
                f"{predictions['demand'].max():.1f} MWh",
                f"{predictions['demand'].mean():.1f} MWh avg"
            )

    with tab3:
        st.markdown(f"""
        ### About this Dashboard
        This dashboard provides energy generation forecasts using machine learning models trained on historical data.

        **Features:**
        - Solar generation prediction
        - Wind generation prediction
        - Demand forecasting
        - Generation mix analysis
        - Timezone support (Currently showing: {selected_timezone})

        **Data Sources:**
        - Historical weather data
        - Past generation records
        - Demand patterns
        """)

if __name__ == "__main__":
    main()
