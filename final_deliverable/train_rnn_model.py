import torch
import pandas as pd
import sqlite3
from hierarchical_rnn_model import HierarchicalEnergyForecaster

def train():
    # Load data
    print("Loading data...")
    conn = sqlite3.connect("energy_data_NE.db")
    
    weather_data = pd.read_sql_query("""
        SELECT time as datetime, temperature, dwpt, humidity, precipitation,
               wdir, windspeed, pres, cloudcover
        FROM historical_weather_data
    """, conn)
    weather_data['datetime'] = pd.to_datetime(weather_data['datetime'])
    
    energy_data = {
        'solar': pd.read_sql_query("SELECT datetime, value FROM SUN_data_NE", conn),
        'wind': pd.read_sql_query("SELECT datetime, value FROM WND_data_NE", conn),
        'demand': pd.read_sql_query("SELECT datetime, Demand as value FROM demand_data_NE", conn)
    }
    conn.close()

    # Initialize model
    print("Initializing model...")
    input_size = 12  # 8 weather features + 4 temporal features
    model = HierarchicalEnergyForecaster(input_size=input_size)
    
    # Training parameters
    num_epochs = 50
    learning_rate = 0.001
    
    # Prepare data
    print("Preparing data...")
    sequences, targets = model.prepare_data(weather_data, energy_data)
    
    # Train
    print("Training model...")
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = torch.nn.MSELoss()
    
    for epoch in range(num_epochs):
        model.train()
        optimizer.zero_grad()
        
        predictions = model(sequences)
        loss = sum(
            criterion(
                predictions[source][str(horizon)],
                torch.FloatTensor(targets[source][str(horizon)])
            )
            for source in ['solar', 'wind', 'demand']
            for horizon in model.forecast_horizons
        )
        
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}')
    
    # Save model
    print("Saving model...")
    torch.save(model.state_dict(), 'hierarchical_rnn_model.pkl')
    print("Training complete!")

if __name__ == "__main__":
    train()