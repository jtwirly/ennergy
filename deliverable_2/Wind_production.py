import requests
import json
import pandas as pd
from datetime import datetime
import os

def fetch_and_save_eia_data(start_time, end_time, api_key, grid_operator=None):
    """
    Fetch data from EIA API and save to CSV file.
    
    Parameters:
    start_time (str): Start time in format 'YYYY-MM-DDThh'
    end_time (str): End time in format 'YYYY-MM-DDThh'
    api_key (str): EIA API key
    grid_operator (str or list, optional): Specific grid operator(s) to filter for (e.g., 'PJM', ['PJM', 'MISO'])
                                         If None, returns data for all operators
    """
    # Construct the URL
    url = f'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/?frequency=hourly&data[0]=value&facets[fueltype][]=SUN&facets[fueltype][]=WND&start={start_time}&end={end_time}&sort[0][column]=fueltype&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}'

    # Send the GET request to the API
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # Extract the data points
        records = []
        for item in data['response']['data']:
            # If grid_operator is specified, only include matching records
            if grid_operator is not None:
                if isinstance(grid_operator, str) and item['respondent'] != grid_operator:
                    continue
                elif isinstance(grid_operator, list) and item['respondent'] not in grid_operator:
                    continue
            
            record = {
                'datetime': item['period'],
                'respondent_code': item['respondent'],
                'respondent_name': item['respondent-name'],
                'fuel_type': item['fueltype'],
                'type_name': item['type-name'],
                'value': float(item['value']),
                'units': item['value-units']
            }
            records.append(record)
        
        if not records:
            print(f"No data found for specified grid operator(s): {grid_operator}")
            return None
            
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Convert datetime strings to datetime objects
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Sort by datetime and fuel type
        df = df.sort_values(['datetime', 'fuel_type'])
        
        # Create filename with grid operator and date range
        grid_suffix = f"_{grid_operator}" if isinstance(grid_operator, str) else "_multiple_grids" if isinstance(grid_operator, list) else ""
        filename = f'eia_renewable_data{grid_suffix}_{start_time[:10]}_{end_time[:10]}.csv'
        
        # Save to CSV
        df.to_csv(f"deliverable_2/{filename}", index=False)
        print(f"Data successfully saved to {filename}")
        
        # Print summary statistics
        print("\nSummary Statistics:")
        print("-" * 50)
        print("\nTotal Generation by Fuel Type:")
        fuel_summary = df.groupby('fuel_type').agg({
            'value': ['sum', 'mean', 'min', 'max', 'count']
        })
        print(fuel_summary)
        
        print("\nHourly Statistics:")
        print(f"Total Hours: {df['datetime'].nunique()}")
        print(f"Date Range: {df['datetime'].min()} to {df['datetime'].max()}")
        
        if grid_operator:
            print(f"\nGrid Operator: {grid_operator}")
        
        # Calculate and print percentage of zero values
        zero_values = (df['value'] == 0).sum()
        total_values = len(df)
        print(f"\nZero Generation Periods: {zero_values} ({(zero_values/total_values)*100:.1f}% of total)")
        
        return df
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        return None

# Example usage
api_key = os.getenv("EIA_API_KEY") #Change to os.getenv(EIA_API_KEY)
start_time = "2024-09-01T00"
end_time = "2024-11-01T00"

# Example 1: Get data for just PJM
df_pjm = fetch_and_save_eia_data(start_time, end_time, api_key, grid_operator='PJM')

# # Example 2: Get data for multiple grid operators
# df_multiple = fetch_and_save_eia_data(start_time, end_time, api_key, grid_operator=['PJM', 'MISO', 'ERCOT'])

# # Example 3: Get all grid operators
# df_all = fetch_and_save_eia_data(start_time, end_time, api_key)


grid_operator="PJM"
# Optional: Create a time series plot if you want to visualize the data
if df_pjm is not None:
    # Pivot the data for plotting
    pivot_df = df_pjm.pivot(index='datetime', columns='fuel_type', values='value')
    
    # Basic time series plot
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(15, 6))
    for col in pivot_df.columns:
        plt.plot(pivot_df.index, pivot_df[col], label=col)
    
    plt.title(f'Renewable Generation - {grid_operator}')
    plt.xlabel('Date')
    plt.ylabel('Generation (MWh)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(f'deliverable_2/generation_plot_{grid_operator}_{start_time[:10]}_{end_time[:10]}.png')
    plt.close()