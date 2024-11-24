# app.py
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import joblib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

class EnergyDashboard:
    def __init__(self):
        """Initialize dashboard with models and database connection"""
        self.load_models()
        self.database_path = "energy_data_NE.db"

    def load_models(self):
        """Load the pre-trained models"""
        try:
            self.models = {
                'solar': joblib.load('solar_model.joblib'),
                'wind': joblib.load('wind_model.joblib'),
                'demand': joblib.load('demand_model.joblib')
            }
            st.success("✅ Models loaded successfully")
        except Exception as e:
            st.error(f"Error loading models: {str(e)}")

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
                         weather_data[['hour', 'month', 'season', 'time_of_day']]], 
                         axis=1)

    def get_predictions(self, start_date):
        """Get predictions for the specified date"""
        conn = sqlite3.connect(self.database_path)
        
        query = f"""
        SELECT time as datetime, temperature, dwpt, humidity, precipitation,
               wdir, windspeed, pres, cloudcover
        FROM historical_weather_data
        WHERE time >= datetime('{start_date}')
        AND time < datetime('{start_date}', '+1 day')
        """
        
        pred_data = pd.read_sql_query(query, conn)
        conn.close()
        
        if pred_data.empty:
            return None
            
        pred_data['datetime'] = pd.to_datetime(pred_data['datetime'])
        X_pred = self.prepare_features(pred_data)
        
        predictions = {'datetime': pred_data['datetime']}
        for source, model in self.models.items():
            predictions[source] = model.predict(X_pred)
            
        return pd.DataFrame(predictions)

    def create_plots(self, predictions):
        """Create interactive plots"""
        fig = make_subplots(
            rows=3, 
            cols=1,
            subplot_titles=(
                'Energy Generation Forecast',
                'Demand Forecast',
                'Generation Mix'
            ),
            vertical_spacing=0.1,
            row_heights=[0.4, 0.3, 0.3]  # Changed from 'heights' to 'row_heights'
        )
        
        # Generation predictions
        for source in ['solar', 'wind']:
            fig.add_trace(
                go.Scatter(
                    x=predictions['datetime'],
                    y=predictions[source],
                    name=source.title(),
                    mode='lines+markers'
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
                line=dict(color='red')
            ),
            row=2, 
            col=1
        )
        
        # Generation mix
        total_gen = predictions['solar'] + predictions['wind']
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions['solar']/total_gen*100),
                name='Solar %',
                marker_color='orange'
            ),
            row=3, 
            col=1
        )
        fig.add_trace(
            go.Bar(
                x=predictions['datetime'],
                y=(predictions['wind']/total_gen*100),
                name='Wind %',
                marker_color='blue'
            ),
            row=3, 
            col=1
        )
        
        # Update layout
        fig.update_layout(
            height=900,
            showlegend=True,
            barmode='stack',
            title_text="Energy Generation and Demand Forecast",
            title_x=0.5,  # Center the title
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Time", row=3, col=1)
        fig.update_yaxes(title_text="Generation (MWh)", row=1, col=1)
        fig.update_yaxes(title_text="Demand (MWh)", row=2, col=1)
        fig.update_yaxes(title_text="Percentage (%)", row=3, col=1)

        return fig

def main():
    st.set_page_config(page_title="Energy Generation Forecast", layout="wide")
    
    st.title("⚡ Energy Generation Forecast Dashboard")
    
    # Initialize dashboard
    dashboard = EnergyDashboard()
    
    # Get available date range
    min_date, max_date = dashboard.get_available_dates()
    
    # Sidebar
    st.sidebar.header("Forecast Settings")
    
    # Show available date range
    st.sidebar.info(f"""
        Available data range:
        - From: {min_date.strftime('%Y-%m-%d')}
        - To: {max_date.strftime('%Y-%m-%d')}
    """)
    
    # Date selection with valid range
    selected_date = st.sidebar.date_input(
        "Select forecast date",
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=min_date.date()
    )
    
    # Time selection
    selected_time = st.sidebar.time_input(
        "Select start time",
        value=datetime.strptime('00:00', '%H:%M').time()
    )
    
    # Combine date and time
    start_datetime = datetime.combine(selected_date, selected_time)
    
    if start_datetime < min_date or start_datetime > max_date:
        st.error(f"""
            Selected date ({start_datetime.strftime('%Y-%m-%d %H:%M')}) is outside available data range.
            Please select a date between:
            {min_date.strftime('%Y-%m-%d %H:%M')} and {max_date.strftime('%Y-%m-%d %H:%M')}
        """)
        return
    
    # Get predictions
    with st.spinner('Generating predictions...'):
        predictions = dashboard.get_predictions(start_datetime)
        
        if predictions is None or predictions.empty:
            st.error(f"""
                No data available for {start_datetime.strftime('%Y-%m-%d %H:%M')}.
                This might be because:
                1. No weather data exists for this date
                2. The date is outside the training period
                
                Try selecting a different date within the available range.
            """)
            return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Forecasts", "📊 Statistics", "ℹ️ Info"])
    
    with tab1:
        # Display plots
        st.plotly_chart(dashboard.create_plots(predictions), use_container_width=True)
        
        # Display raw data if requested
        if st.checkbox("Show raw data"):
            st.dataframe(predictions)
    
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
        st.markdown("""
        ### About this Dashboard
        This dashboard provides energy generation forecasts using machine learning models trained on historical data.
        
        **Features:**
        - Solar generation prediction
        - Wind generation prediction
        - Demand forecasting
        - Generation mix analysis
        
        **Data Sources:**
        - Historical weather data
        - Past generation records
        - Demand patterns
        """)

if __name__ == "__main__":
    main()