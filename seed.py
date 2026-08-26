"""
Build and seed shane.db -- a small records-destruction business database.

Run once:  python seed.py
Re-running drops and rebuilds everything, so it's safe to run again.

SEED DISTRIBUTION (quote_request, 18 rows total)
  10  inside 30 days, HAS a scheduled pickup     -> excluded from the answer
   5  inside 30 days, NO pickup                  -> THE ANSWER
   3  outside 30 days, NO pickup                 -> excluded by the date filter
   5  of the 8 pickup-less rows have customer_id NULL (never converted)

GOLDEN ANSWER
  "Which quote requests from the last 30 days have no scheduled pickup?"
  -> 5 rows: quote_request_id 11, 12, 13, 14, 15
"""

import sqlite3
from datetime import date, timedelta

DB = "shane.db"

TODAY = date.today()


def days_ago(n):
    """ISO date string n days before today. SQLite compares dates as text,
    so YYYY-MM-DD is the only format that sorts correctly."""
    return (TODAY - timedelta(days=n)).isoformat()


SCHEMA = """
DROP TABLE IF EXISTS pickups;
DROP TABLE IF EXISTS quote_request;
DROP TABLE IF EXISTS customer;

CREATE TABLE customer (
    customer_id           INTEGER PRIMARY KEY,
    customer_name         TEXT NOT NULL,
    customer_main_contact TEXT,
    customer_address      TEXT,
    create_date           TEXT NOT NULL,
    update_date           TEXT NOT NULL
);

CREATE TABLE quote_request (
    quote_request_id        INTEGER PRIMARY KEY,
    customer_id             INTEGER,
    quote_request_raw_string TEXT,
    quote_request_contact   TEXT,
    service_type            TEXT CHECK (service_type IN
                              ('shredding','scanning','hard drive destruction')),
    box_count               INTEGER,
    volume_stated_as        TEXT,
    urgency                 TEXT,
    create_date             TEXT NOT NULL,
    update_date             TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE pickups (
    pickup_id        INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    quote_request_id INTEGER NOT NULL,
    scheduled_date   TEXT NOT NULL,
    completed_date   TEXT,
    pickup_outcome   TEXT CHECK (pickup_outcome IN
                       ('success','customer not available','pickup not feasible')),
    create_date      TEXT NOT NULL,
    update_date      TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (quote_request_id) REFERENCES quote_request(quote_request_id)
);
"""

CUSTOMERS = [
    (1,  "Piedmont Family Dentistry",    "Dana Whitlock",  "142 Cherry Rd, Rock Hill SC"),
    (2,  "Catawba Valley Orthopedics",   "Reg Alameda",    "88 Ebenezer Ave, Rock Hill SC"),
    (3,  "Fort Mill Title & Escrow",     "Sylvia Boone",   "3312 Hwy 21, Fort Mill SC"),
    (4,  "Anderson Krebs LLP",           "Marcus Anderson","705 Main St, Lancaster SC"),
    (5,  "Waxhaw Pediatric Associates",  "Tomás Reyna",    "19 Providence Rd, Waxhaw NC"),
    (6,  "Steele Creek Insurance Group", "Bettina Salas",  "4400 Sandy Porter Rd, Charlotte NC"),
    (7,  "Union County Physical Therapy","Ori Nakashima",  "2201 Roosevelt Blvd, Monroe NC"),
    (8,  "Ballantyne Wealth Partners",   "Grace Odum",     "15720 Brixham Hill Ave, Charlotte NC"),
    (9,  "Indian Land Veterinary",       "Hugh Petrarca",  "1010 Charlotte Hwy, Indian Land SC"),
    (10, "Tega Cay Dermatology",         "Nadia Falkenrath","2 Stonecrest Blvd, Tega Cay SC"),
]

# (quote_id, customer_id, service, box_count, volume_stated_as, urgency, days_ago, contact)
QUOTES = [
    # --- 10 inside 30 days, WILL get a pickup ---
    (1,  1,  "shredding",               24,  "about two dozen boxes",            "within a month",  28, "Dana Whitlock"),
    (2,  2,  "shredding",               60,  "sixty banker boxes",               "no rush",         26, "Reg Alameda"),
    (3,  3,  "scanning",                12,  "a dozen or so",                    "end of quarter",  24, "Sylvia Boone"),
    (4,  4,  "shredding",               95,  "roughly 95 boxes",                 "urgent",          21, "Marcus Anderson"),
    (5,  5,  "hard drive destruction",  None,"eight old server drives",          "this month",      19, "Tomás Reyna"),
    (6,  6,  "shredding",               40,  "40 boxes give or take",            None,              16, "Bettina Salas"),
    (7,  7,  "scanning",                18,  "18 boxes of patient files",        "soon",            13, "Ori Nakashima"),
    (8,  8,  "shredding",               150, "a hundred and fifty boxes",        "before year end",  9, "Grace Odum"),
    (9,  9,  "shredding",               22,  "22 boxes",                         None,               6, "Hugh Petrarca"),
    (10, 10, "hard drive destruction",  None,"a stack of drives and a few laptops","not urgent",     3, "Nadia Falkenrath"),

    # --- 5 inside 30 days, NO pickup  <-- THE GOLDEN ANSWER ---
    (11, None, "shredding",             None, "a few boxes, maybe more once we get into the back closet", None, 27, "front desk"),
    (12, None, "shredding",             30,   "about 30 boxes",                  "asap",            18, "Kelly"),
    (13, 2,    "scanning",              None, "not sure yet, still sorting",      None,             11, "Reg Alameda"),
    (14, None, "hard drive destruction",None, "old computers from the remodel",   None,              5, None),
    (15, 6,    "shredding",             8,    "eight boxes",                      "flexible",        2, "Bettina Salas"),

    # --- 3 outside 30 days, NO pickup (the date-filter trap) ---
    (16, None, "shredding",             45,   "45 boxes",                         "whenever",       47, "Pam in accounting"),
    (17, 4,    "scanning",              20,   "twenty boxes of closed files",     None,             62, "Marcus Anderson"),
    (18, None, "shredding",             None, "a whole storage unit's worth",     "urgent",         88, None),
]

RAW_EMAIL_11 = (
    "Hi - we're closing out our old records room and need to get rid of a bunch of files, "
    "probably a few boxes, maybe more once we get into the back closet. Some of it is patient "
    "billing stuff from before we switched systems so it needs to be done right. Can you give me "
    "a price and let me know how soon someone could come out? We're off Highway 21 near the Food Lion."
)

# (pickup_id, customer_id, quote_id, scheduled_days_ago, completed_days_ago, outcome)
PICKUPS = [
    (1,  1,  1,  20, 20, "success"),
    (2,  2,  2,  18, 18, "success"),
    (3,  3,  3,  15, 15, "success"),
    (4,  4,  4,  14, 14, "customer not available"),
    (5,  5,  5,  12, 12, "success"),
    (6,  6,  6,  10, 10, "success"),
    (7,  7,  7,   7,  7, "pickup not feasible"),
    (8,  8,  8,   4,  4, "success"),
    (9,  9,  9,  -2, None, None),    # scheduled 2 days in the FUTURE, not yet done
    (10, 10, 10, -6, None, None),    # scheduled 6 days out
]


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executescript(SCHEMA)

    for cid, name, contact, addr in CUSTOMERS:
        stamp = days_ago(120)
        cur.execute(
            "INSERT INTO customer VALUES (?,?,?,?,?,?)",
            (cid, name, contact, addr, stamp, stamp),
        )

    for qid, cid, svc, boxes, vol, urg, ago, contact in QUOTES:
        stamp = days_ago(ago)
        raw = RAW_EMAIL_11 if qid == 11 else None
        cur.execute(
            "INSERT INTO quote_request VALUES (?,?,?,?,?,?,?,?,?,?)",
            (qid, cid, raw, contact, svc, boxes, vol, urg, stamp, stamp),
        )

    for pid, cid, qid, sched, comp, outcome in PICKUPS:
        cur.execute(
            "INSERT INTO pickups VALUES (?,?,?,?,?,?,?,?)",
            (
                pid, cid, qid,
                days_ago(sched),
                days_ago(comp) if comp is not None else None,
                outcome,
                days_ago(sched), days_ago(sched),
            ),
        )

    conn.commit()

    # Prove the golden answer before anything else touches this database.
    check = """
        SELECT q.quote_request_id
        FROM quote_request q
        LEFT JOIN pickups p ON p.quote_request_id = q.quote_request_id
        WHERE p.pickup_id IS NULL
          AND q.create_date >= date('now','-30 days')
        ORDER BY q.quote_request_id
    """
    rows = [r[0] for r in cur.execute(check).fetchall()]
    print(f"quotes in last 30 days with no pickup: {rows}")
    print(f"count = {len(rows)}  (expected 5: [11, 12, 13, 14, 15])")

    conn.close()


if __name__ == "__main__":
    main()
