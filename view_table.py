import sqlite3

# Connect to the database
conn = sqlite3.connect('data_base.db')
cursor = conn.cursor()

# Fetch data from the weather table
cursor.execute('SELECT * FROM weather')
rows = cursor.fetchall()

# Print the fetched data
for row in rows:
    print(row)

# Close the connection
conn.close()
