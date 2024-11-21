import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

def fetch_and_save_eia_data(start_time, end_time, api_key, source, grid_operator=None):
    """
    Fetch data from EIA API in 5-day increments, with intelligent file concatenation.
    
    Parameters:
    start_time (str): Start time in format 'YYYY-MM-DDThh'
    end_time (str): End time in format 'YYYY-MM-DDThh'
    api_key (str): EIA API key
    source (str): Fuel type to fetch
    grid_operator (str or list, optional): Specific grid operator(s) to filter for
    
    Returns:
    pd.DataFrame: Fetched and processed data
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    try:
        # Validate inputs
        if not api_key:
            raise ValueError("API key is required")
        
        # Convert start and end times to datetime objects
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H")
        
        # Validate time range
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")
        
        # Initialize an empty list to hold DataFrames
        all_data = []
        
        # Loop through the date range in 5-day increments
        current_time = start_time
        while current_time < end_time:
            # Define the next range, ensuring we don't exceed the end_time
            next_time = min(current_time + timedelta(days=5), end_time)
            
            # Construct the API URL
            url = (f'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/'
                   f'?frequency=hourly&data[0]=value&facets[fueltype][]={source}'
                   f'&start={current_time.strftime("%Y-%m-%dT%H")}'
                   f'&end={next_time.strftime("%Y-%m-%dT%H")}'
                   f'&sort[0][column]=fueltype&sort[0][direction]=desc'
                   f'&offset=0&length=5000&api_key={api_key}')
            
            try:
                # Send the GET request to the API with timeout
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # Raise an exception for bad status codes
                
                data = response.json()
                
                # Extract the data points
                records = []
                for item in data['response']['data']:
                    # Filter by grid operator if specified
                    if grid_operator is not None:
                        if isinstance(grid_operator, str) and item['respondent'] != grid_operator:
                            continue
                        elif isinstance(grid_operator, list) and item['respondent'] not in grid_operator:
                            continue
                    
                    try:
                        record = {
                            'datetime': item['period'],
                            'respondent_code': item['respondent'],
                            'respondent_name': item.get('respondent-name', 'Unknown'),
                            'fuel_type': item['fueltype'],
                            'type_name': item.get('type-name', 'Unknown'),
                            'value': item['value'],
                            'units': item['value-units']
                        }
                        records.append(record)
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Skipping record due to error: {e}")
                
                # Append to the list if records are found
                if records:
                    df = pd.DataFrame(records)
                    all_data.append(df)
                
            except requests.RequestException as e:
                logger.error(f"API request failed for range {current_time} to {next_time}: {e}")
            
            # Move to the next range
            current_time = next_time
        
        # Concatenate all DataFrames if any data was fetched
        if all_data:
            full_data = pd.concat(all_data, ignore_index=True)
            
            # Convert datetime strings to datetime objects and sort by datetime and fuel type
            full_data['datetime'] = pd.to_datetime(full_data['datetime'])
            full_data = full_data.sort_values(by=['datetime', 'fuel_type'])
            
            # Ensure output directory exists
            os.makedirs('deliverable_2', exist_ok=True)
            
            # Create filename with grid operator and date range
            grid_suffix = f"_{grid_operator}" if isinstance(grid_operator, str) else "_multiple_grids" if isinstance(grid_operator, list) else ""
            filename = f'{source}_data{grid_suffix}.csv'
            output_path = os.path.join('deliverable_2', filename)
            
            # Check if file exists and handle concatenation
            if os.path.exists(output_path):
                # Read existing data
                existing_data = pd.read_csv(output_path, parse_dates=['datetime'])
                
                # Determine concatenation strategy based on data timestamps
                if full_data['datetime'].min() < existing_data['datetime'].min():
                    # New data is older, prepend
                    merged_data = pd.concat([full_data, existing_data]).drop_duplicates().sort_values('datetime')
                else:
                    # New data is newer, append
                    merged_data = pd.concat([existing_data, full_data]).drop_duplicates().sort_values('datetime')
                
                # Save merged data
                merged_data.to_csv(output_path, index=False)
                logger.info(f"Data successfully merged and saved to {output_path}")
            else:
                # No existing file, save new data
                full_data.to_csv(output_path, index=False)
                logger.info(f"Data successfully saved to {output_path}")
            
            return full_data
        else:
            logger.warning("No data was fetched.")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return pd.DataFrame()

def main():
    """
    Main function to demonstrate script usage with error handling.
    """
    # Use environment variable for API key with fallback
    api_key = os.getenv("EIA_API_KEY")
    
    if not api_key:
        print("Error: EIA_API_KEY environment variable not set")
        return
    
    try:
        start_time = "2022-10-27T00"
        end_time = "2022-10-29T00"
        
        # Fetch data for PJM grid operator
        df = fetch_and_save_eia_data(start_time, end_time, api_key, "NG", grid_operator='NE')
        
        # Optional: print basic info about fetched data
        if not df.empty:
            print(f"Fetched {len(df)} records")
            print(df.head())
    
    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()