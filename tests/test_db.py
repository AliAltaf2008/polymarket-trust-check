import sqlite3

from trustcheck.db import COLUMNS, init_db, upsert_record

RECORD = {
    "id": "555",
    "question": "Will X happen?",
    "slug": "will-x-happen",
    "condition_id": "0xabc",
    "event_id": "999",
    "end_date": "2025-01-20T12:00:00Z",
    "volume": 2500000.5,
    "liquidity": 1000.25,
    "closed": True,
    "close_time": "2025-01-20T22:51:36Z",
    "anchor_time": "2025-01-20T12:00:00Z",
    "winner": "Yes",
    "ref_price": 0.62,
    "ref_ts": 1736172000,
    "tags": '["Politics"]',
    "is_sports": False,
    "was_disputed": True,
    "yes_token_id": "111", 
}


def make_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def count(conn):
    return conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]


def test_one_upsert_gives_one_row():
    conn = make_conn()
    upsert_record(conn, RECORD)
    assert count(conn) == 1


def test_same_record_twice_still_one_row():
    conn = make_conn()
    upsert_record(conn, RECORD)
    upsert_record(conn, RECORD)
    assert count(conn) == 1


def test_different_ids_give_different_rows():
    conn = make_conn()
    upsert_record(conn, RECORD)
    upsert_record(conn, {**RECORD, "id": "556"})
    assert count(conn) == 2


def test_changed_value_updates_the_row():
    conn = make_conn()
    upsert_record(conn, RECORD)
    upsert_record(conn, {**RECORD, "ref_price": 0.9})
    price = conn.execute("SELECT ref_price FROM markets WHERE id = '555'").fetchone()[0]
    assert price == 0.9


def test_booleans_are_stored_as_0_and_1():
    conn = make_conn()
    upsert_record(conn, RECORD)
    row = conn.execute(
        "SELECT closed, is_sports, was_disputed FROM markets WHERE id = '555'"
    ).fetchone()
    assert row == (1, 0, 1)


def test_missing_optional_field_is_stored_as_null():
    conn = make_conn()
    record = {k: v for k, v in RECORD.items() if k != "ref_price"}
    upsert_record(conn, record)
    price = conn.execute("SELECT ref_price FROM markets WHERE id = '555'").fetchone()[0]
    assert price is None


def test_extra_keys_are_ignored():
    conn = make_conn()
    upsert_record(conn, RECORD)
    assert count(conn) == 1


def test_columns_list_matches_the_table():
    conn = make_conn()
    table_columns = [row[1] for row in conn.execute("PRAGMA table_info(markets)")]
    assert sorted(table_columns) == sorted(COLUMNS)