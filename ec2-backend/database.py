import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "medicine_tracker.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        generic_name TEXT,
        batch_number TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        dosage_form TEXT NOT NULL DEFAULT 'Tablet',
        manufacturer TEXT,
        supplier TEXT,
        quantity INTEGER NOT NULL DEFAULT 0,
        min_threshold INTEGER NOT NULL DEFAULT 15,
        unit_price REAL NOT NULL DEFAULT 0.0,
        mfg_date TEXT,
        expiry_date TEXT NOT NULL,
        storage_location TEXT DEFAULT 'Shelf A-1',
        prescription_required INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        batch_number TEXT,
        type TEXT NOT NULL, -- RESTOCK, DISPENSE, ADJUSTMENT
        quantity_change INTEGER NOT NULL,
        resulting_quantity INTEGER NOT NULL,
        reason TEXT,
        performed_by TEXT DEFAULT 'Staff Pharmacist',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT NOT NULL, -- critical, warning, info
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def seed_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if table has data
    cursor.execute("SELECT COUNT(*) FROM medicines")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    today = date.today()
    sample_medicines = [
        {
            "name": "Paracetamol 500mg",
            "generic_name": "Acetaminophen",
            "batch_number": "BATCH-PCM-2026-01",
            "category": "Analgesics & Antipyretics",
            "dosage_form": "Tablet",
            "manufacturer": "Cipla Ltd",
            "supplier": "Apex Pharma Logistics",
            "quantity": 180,
            "min_threshold": 30,
            "unit_price": 2.50,
            "mfg_date": (today - timedelta(days=180)).isoformat(),
            "expiry_date": (today + timedelta(days=240)).isoformat(),
            "storage_location": "Rack A-1",
            "prescription_required": 0
        },
        {
            "name": "Amoxicillin 500mg",
            "generic_name": "Amoxicillin Trihydrate",
            "batch_number": "BATCH-AMX-2025-88",
            "category": "Antibiotics",
            "dosage_form": "Capsule",
            "manufacturer": "Sun Pharmaceutical",
            "supplier": "MediSupply Direct",
            "quantity": 12, # Low stock! (Threshold 25)
            "min_threshold": 25,
            "unit_price": 14.20,
            "mfg_date": (today - timedelta(days=300)).isoformat(),
            "expiry_date": (today + timedelta(days=18)).isoformat(), # Expiring soon! (<30 days)
            "storage_location": "Rack B-2",
            "prescription_required": 1
        },
        {
            "name": "Azithromycin 250mg",
            "generic_name": "Azithromycin Dihydrate",
            "batch_number": "BATCH-AZT-2025-14",
            "category": "Antibiotics",
            "dosage_form": "Tablet",
            "manufacturer": "Pfizer Health",
            "supplier": "Global Care Distribution",
            "quantity": 4, # Low stock!
            "min_threshold": 20,
            "unit_price": 22.00,
            "mfg_date": (today - timedelta(days=400)).isoformat(),
            "expiry_date": (today - timedelta(days=5)).isoformat(), # Already expired!
            "storage_location": "Rack B-3 (Quarantine)",
            "prescription_required": 1
        },
        {
            "name": "Metformin 500mg",
            "generic_name": "Metformin Hydrochloride",
            "batch_number": "BATCH-MET-2026-45",
            "category": "Antidiabetic",
            "dosage_form": "Tablet",
            "manufacturer": "Dr. Reddy's Laboratories",
            "supplier": "Prime Care Distributors",
            "quantity": 320,
            "min_threshold": 50,
            "unit_price": 4.10,
            "mfg_date": (today - timedelta(days=120)).isoformat(),
            "expiry_date": (today + timedelta(days=360)).isoformat(),
            "storage_location": "Rack C-1",
            "prescription_required": 1
        },
        {
            "name": "Atorvastatin 20mg",
            "generic_name": "Atorvastatin Calcium",
            "batch_number": "BATCH-ATV-2025-72",
            "category": "Cardiovascular",
            "dosage_form": "Tablet",
            "manufacturer": "Lupin Pharmaceuticals",
            "supplier": "HealthLink Wholesale",
            "quantity": 45,
            "min_threshold": 20,
            "unit_price": 18.50,
            "mfg_date": (today - timedelta(days=220)).isoformat(),
            "expiry_date": (today + timedelta(days=25)).isoformat(), # Expiring in 25 days!
            "storage_location": "Rack C-2",
            "prescription_required": 1
        },
        {
            "name": "Cetirizine 10mg",
            "generic_name": "Cetirizine Dihydrochloride",
            "batch_number": "BATCH-CTZ-2026-09",
            "category": "Antihistamines & Allergy",
            "dosage_form": "Tablet",
            "manufacturer": "Glenmark Pharma",
            "supplier": "Apex Pharma Logistics",
            "quantity": 140,
            "min_threshold": 30,
            "unit_price": 3.75,
            "mfg_date": (today - timedelta(days=90)).isoformat(),
            "expiry_date": (today + timedelta(days=450)).isoformat(),
            "storage_location": "Rack D-1",
            "prescription_required": 0
        },
        {
            "name": "Omeprazole 20mg",
            "generic_name": "Omeprazole Magnesium",
            "batch_number": "BATCH-OMP-2025-63",
            "category": "Gastrointestinal",
            "dosage_form": "Capsule",
            "manufacturer": "Torrent Pharma",
            "supplier": "MediSupply Direct",
            "quantity": 6, # Low stock!
            "min_threshold": 30,
            "unit_price": 8.00,
            "mfg_date": (today - timedelta(days=260)).isoformat(),
            "expiry_date": (today + timedelta(days=70)).isoformat(),
            "storage_location": "Rack D-3",
            "prescription_required": 0
        },
        {
            "name": "Insulin Glargine 100 IU/ml",
            "generic_name": "Insulin Glargine",
            "batch_number": "BATCH-INS-2025-99",
            "category": "Antidiabetic",
            "dosage_form": "Injection",
            "manufacturer": "Sanofi Healthcare",
            "supplier": "BioCold Chain Distribution",
            "quantity": 0, # Out of stock!
            "min_threshold": 15,
            "unit_price": 540.00,
            "mfg_date": (today - timedelta(days=150)).isoformat(),
            "expiry_date": (today + timedelta(days=120)).isoformat(),
            "storage_location": "Refrigerator Cold Bay #2 (2-8°C)",
            "prescription_required": 1
        },
        {
            "name": "Salbutamol Inhaler 100mcg",
            "generic_name": "Albuterol Sulfate",
            "batch_number": "BATCH-SLB-2026-30",
            "category": "Respiratory",
            "dosage_form": "Inhaler",
            "manufacturer": "GlaxoSmithKline (GSK)",
            "supplier": "Apex Pharma Logistics",
            "quantity": 28,
            "min_threshold": 10,
            "unit_price": 145.00,
            "mfg_date": (today - timedelta(days=80)).isoformat(),
            "expiry_date": (today + timedelta(days=320)).isoformat(),
            "storage_location": "Rack E-1",
            "prescription_required": 1
        },
        {
            "name": "Ibuprofen 400mg",
            "generic_name": "Ibuprofen",
            "batch_number": "BATCH-IBU-2025-33",
            "category": "Analgesics & Antipyretics",
            "dosage_form": "Tablet",
            "manufacturer": "Abbott India",
            "supplier": "Global Care Distribution",
            "quantity": 210,
            "min_threshold": 40,
            "unit_price": 3.20,
            "mfg_date": (today - timedelta(days=310)).isoformat(),
            "expiry_date": (today - timedelta(days=20)).isoformat(), # Expired!
            "storage_location": "Rack A-3 (Disposal Pending)",
            "prescription_required": 0
        },
        {
            "name": "Ciprofloxacin Eye Drops 0.3%",
            "generic_name": "Ciprofloxacin HCl",
            "batch_number": "BATCH-CIP-2026-11",
            "category": "Ophthalmic",
            "dosage_form": "Drops",
            "manufacturer": "Alcon Laboratories",
            "supplier": "MediSupply Direct",
            "quantity": 18,
            "min_threshold": 15,
            "unit_price": 62.50,
            "mfg_date": (today - timedelta(days=60)).isoformat(),
            "expiry_date": (today + timedelta(days=15)).isoformat(), # Expiring in 15 days!
            "storage_location": "Rack F-2",
            "prescription_required": 1
        },
        {
            "name": "Pantoprazole 40mg",
            "generic_name": "Pantoprazole Sodium",
            "batch_number": "BATCH-PAN-2026-55",
            "category": "Gastrointestinal",
            "dosage_form": "Tablet",
            "manufacturer": "Sun Pharmaceutical",
            "supplier": "HealthLink Wholesale",
            "quantity": 95,
            "min_threshold": 25,
            "unit_price": 9.80,
            "mfg_date": (today - timedelta(days=45)).isoformat(),
            "expiry_date": (today + timedelta(days=400)).isoformat(),
            "storage_location": "Rack D-2",
            "prescription_required": 0
        }
    ]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in sample_medicines:
        cursor.execute("""
        INSERT INTO medicines (
            name, generic_name, batch_number, category, dosage_form,
            manufacturer, supplier, quantity, min_threshold, unit_price,
            mfg_date, expiry_date, storage_location, prescription_required,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["name"], item["generic_name"], item["batch_number"],
            item["category"], item["dosage_form"], item["manufacturer"],
            item["supplier"], item["quantity"], item["min_threshold"],
            item["unit_price"], item["mfg_date"], item["expiry_date"],
            item["storage_location"], item["prescription_required"],
            now_str, now_str
        ))
        med_id = cursor.lastrowid

        # Add initial transaction
        cursor.execute("""
        INSERT INTO transactions (
            medicine_id, medicine_name, batch_number, type,
            quantity_change, resulting_quantity, reason, performed_by, timestamp
        ) VALUES (?, ?, ?, 'INITIAL', ?, ?, 'Initial Stock Inward', 'Admin', ?)
        """, (med_id, item["name"], item["batch_number"], item["quantity"], item["quantity"], now_str))

    conn.commit()
    conn.close()
