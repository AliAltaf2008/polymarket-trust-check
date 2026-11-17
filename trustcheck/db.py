import json
import sqlite3

DB_PATH = "data/trustcheck.db"
MARKETS_JSON = "data/markets.json"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db(conn):
    conn.execute(
        """

        CREATE TABLE IF NOT EXISTS markets (
            id TEXT PRIMARY KEY,
            question TEXT,
            slug TEXT,
            condition_id TEXT,
            event_id TEXT,
            end_date TEXT,
            volume REAL,
            liquidity REAL,
            closed INTEGER
            close_time TEXT,
            winner TEXT,
            ref_price REAL,
            tags TEXT
            is_sports INTEGER,
            was_disputed INTEGER
        )
        """

    )

    conn.commit()


def market_to_row(m):
   #turn one cleaned market into a tuple of 9 values
    return (
        m["id"],
        m["question"],
        m["slug"],
        m["condition_id"],
        m["event_id"],
        m["end_date"],
        m["volume"],
        m["liquidity"],
        int(m["closed"]),  # True/False becomes 1/0
    )

UPSERT_SQL = """
INSERT INTO markets
    (id, question, slug, condition_id, event_id, end_date, volume, liquidity, closed)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    question = excluded.question,
    slug = excluded.slug,
    condition_id = excluded.condition_id,
    event_id = excluded.event_id,
    end_date = excluded.end_date,
    volume = excluded.volume,
    liquidity = excluded.liquidity,
    closed = excluded.closed
"""

def load_markets(conn, path=MARKETS_JSON):
    with open(path) as f:
        markets = json.load(f)

    rows = [market_to_row(m) for m in markets]

    conn.executemany(UPSERT_SQL, rows)
    conn.commit()
    #How many new markets were added into the table
    return len(rows)

def count_markets(conn):
    #Return the total rows in the table
    return conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]


def top_markets(conn, n):
    #order by volume and sort the biggest first. keep only n rows
    return conn.execute(
        "SELECT question, volume FROM markets ORDER BY volume DESC LIMIT ?",
        (n,),
    ).fetchall()

if __name__ == "__main__":
    conn = get_connection()
    init_db(conn)
    inserted = load_markets(conn)
    print(f"Inserted {inserted} markets | table now has {count_markets(conn)}")
    for question, volume in top_markets(conn, 5):
        #Cleaner output for volume
        print(f"{volume: >15,.0f} {question}")
    conn.close()