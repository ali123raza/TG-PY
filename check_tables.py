import sqlite3
conn = sqlite3.connect('data/tgpy.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]
print('All tables:', tables)
print('peers:', 'peers' in tables)
print('contacts:', 'contacts' in tables)
conn.close()
