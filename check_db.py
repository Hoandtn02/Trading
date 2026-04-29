import sqlite3
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Check stock_data table
c.execute("SELECT COUNT(*) FROM stock_data")
print("StockData count:", c.fetchone()[0])

# Check stock_analysis table
c.execute("SELECT COUNT(*) FROM stock_analysis")
print("StockAnalysis count:", c.fetchone()[0])

# Get sample data
c.execute("SELECT symbol, price FROM stock_data LIMIT 5")
print("\nSample stocks:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")
