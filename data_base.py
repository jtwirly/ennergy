import sqlite3

# Connect to SQLite database
connection = sqlite3.connect("weather.db")

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Use executescript to run multiple commands
cursor.executescript("""
CREATE TABLE Location (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    elevation REAL
);

CREATE TABLE WeatherData (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    temperature REAL,
    humidity REAL,
    wind_speed REAL,
    cloud_cover REAL,
    FOREIGN KEY(location_id) REFERENCES Location(location_id)
);

CREATE TABLE SolarIrradiance (
    irradiance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    GHI REAL,
    DNI REAL,
    DHI REAL,
    FOREIGN KEY(location_id) REFERENCES Location(location_id)
);

CREATE TABLE EnergyProduction (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    power_output REAL,
    FOREIGN KEY(location_id) REFERENCES Location(location_id)
);
""")

# Commit the changes
connection.commit()

# Close the connection
connection.close()
