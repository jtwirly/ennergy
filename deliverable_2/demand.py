import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

def fetch_and_save_demand_data(start_time, end_time, api_key, region='NE'):
    """
    Fetch demand data from EIA API with intelligent file concatenation.
    
    Parameters:
    start_time (str): Start time in format 'YYYY-MM-DDThh'
    end_time (str): End time in format 'YYYY-MM-DDThh'
    api_key (str): EIA API key
    region (str, optional): Specific region to fetch data for. Defaults to 'NE'.
    
    Returns:
    pd.DataFrame: Fetched and processed demand data
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)


    # Validate inputs
    if not api_key:
        raise ValueError("API key is required")
    
    # Construct the full API URL
    url = f"https://api.eia.gov/v2/electricity/rto/region-data/data/?frequency=hourly&data[0]=value&facets[respondent][]=NE&facets[type][]=D&facets[type][]=NG&start={start_time}&end={end_time}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"

    # Send the GET request to the API with timeout
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    print(data)

#             # Extract the data points
#             records = []
#             for item in data['response']['data']:
#                 try:
#                     record = {
#                         'datetime': item['period'],
#                         'respondent_code': item['respondent'],
#                         'value': item['value']
#                     }
#                     records.append(record)
#                 except (KeyError, ValueError) as e:
#                     logger.warning(f"Skipping record due to error: {e}")
            
#             # Create DataFrame if records are found
#             if records:
#                 full_data = pd.DataFrame(records)
                
#                 # Convert datetime strings to datetime objects and sort
#                 full_data['datetime'] = pd.to_datetime(full_data['datetime'])
#                 full_data = full_data.sort_values('datetime')
                
#                 # Ensure output directory exists
#                 os.makedirs('deliverable_2', exist_ok=True)
                
#                 # Create filename with region
#                 filename = f'demand_data_{region}.csv'
#                 output_path = os.path.join('deliverable_2', filename)
                
#                 # Check if file exists and handle concatenation
#                 if os.path.exists(output_path):
#                     existing_data = pd.read_csv(output_path, parse_dates=['datetime'])
                    
#                     # Determine concatenation strategy based on data timestamps
#                     if full_data['datetime'].min() < existing_data['datetime'].min():
#                         # New data is older, prepend
#                         merged_data = pd.concat([full_data, existing_data]).drop_duplicates().sort_values('datetime')
#                     else:
#                         # New data is newer, append
#                         merged_data = pd.concat([existing_data, full_data]).drop_duplicates().sort_values('datetime')
                    
#                     # Save merged data
#                     merged_data.to_csv(output_path, index=False)
#                     logger.info(f"Demand data successfully merged and saved to {output_path}")
#                 else:
#                     # No existing file, save new data
#                     full_data.to_csv(output_path, index=False)
#                     logger.info(f"Demand data successfully saved to {output_path}")
                
#                 return full_data
#             else:
#                 logger.warning("No demand data was fetched.")
#                 return pd.DataFrame()
        
#         except requests.RequestException as e:
#             logger.error(f"API request failed: {e}")
#             return pd.DataFrame()
    
#     except Exception as e:
#         logger.error(f"An unexpected error occurred: {e}")
#         return pd.DataFrame()

# def main():
#     """
#     Main function to demonstrate script usage with error handling.
#     """
api_key = os.getenv("EIA_API_KEY")
    
#     if not api_key:
#         print("Error: EIA_API_KEY environment variable not set")
#         return
    
#     try:
start_time = "2024-10-26T23"
end_time = "2024-10-27T00"

#         # Fetch demand data for New England region
#         df = fetch_and_save_demand_data(start_time, end_time, api_key)
fetch_and_save_demand_data(start_time,end_time,api_key)
        
#         # Optional: print basic info about fetched data
#         if not df.empty:
#             print(f"Fetched {len(df)} demand records")
#             print(df.head())
    
#     except Exception as e:
#         print(f"Error in main execution: {e}")

# if __name__ == "__main__":
#     main()