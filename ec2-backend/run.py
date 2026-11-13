import os
from datetime import datetime, date, timedelta
from app import create_app
from app.models import db, User, Medicine, UsageLog, Alert
from app.services.alert_service import check_and_generate_alerts

env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

def init_database_tables():
    """Initializes tables and populates starter demo data if database is empty."""
    with app.app_context():
        # Create all tables (MySQL or SQLite)
        db.create_all()

        # Check if database is already populated
        if User.query.first():
            return

        print("\n[Database Setup] Seeding default pharmacy account and realistic medicines...")

        # 1. Create Default Demo Pharmacy User
        demo_user = User(
            name="City Care Central Pharmacy",
            email="admin@pharmacy.com",
            role="pharmacy"
        )
        demo_user.set_password("admin123")
        db.session.add(demo_user)
        db.session.flush()

        # 2. Seed Realistic Medicines (Expired, Expiring Soon, Low Stock, Normal)
        today = date.today()
        sample_medicines = [
            {
                "name": "Paracetamol 650mg",
                "batch_number": "BATCH-PCM-2026-01",
                "category": "Analgesics & Antipyretics",
                "quantity": 250,
                "min_stock_level": 50,
                "price": 3.50,
                "expiry_date": today + timedelta(days=240),
                "supplier": "Cipla Pharmaceuticals Ltd"
            },
            {
                "name": "Amoxicillin 500mg",
                "batch_number": "BATCH-AMX-2025-88",
                "category": "Antibiotics",
                "quantity": 14,  # LOW STOCK (<= 25) & EXPIRING IN 18 DAYS!
                "min_stock_level": 25,
                "price": 14.20,
                "expiry_date": today + timedelta(days=18),
                "supplier": "Sun Pharmaceutical Ind."
            },
            {
                "name": "Azithromycin 250mg",
                "batch_number": "BATCH-AZT-2025-14",
                "category": "Antibiotics",
                "quantity": 6,   # LOW STOCK & EXPIRED!
                "min_stock_level": 20,
                "price": 22.00,
                "expiry_date": today - timedelta(days=5),
                "supplier": "Global Care Distribution"
            },
            {
                "name": "Metformin 500mg",
                "batch_number": "BATCH-MET-2026-45",
                "category": "Antidiabetic",
                "quantity": 380,
                "min_stock_level": 50,
                "price": 4.10,
                "expiry_date": today + timedelta(days=360),
                "supplier": "Dr. Reddy's Laboratories"
            },
            {
                "name": "Atorvastatin 20mg",
                "batch_number": "BATCH-ATV-2025-72",
                "category": "Cardiovascular",
                "quantity": 45,
                "min_stock_level": 20,
                "price": 18.50,
                "expiry_date": today + timedelta(days=24),  # EXPIRING IN 24 DAYS!
                "supplier": "Lupin Pharmaceuticals"
            },
            {
                "name": "Cetirizine 10mg",
                "batch_number": "BATCH-CTZ-2026-09",
                "category": "Antihistamines & Allergy",
                "quantity": 160,
                "min_stock_level": 30,
                "price": 3.75,
                "expiry_date": today + timedelta(days=450),
                "supplier": "Apex Pharma Logistics"
            },
            {
                "name": "Omeprazole 20mg",
                "batch_number": "BATCH-OMP-2025-63",
                "category": "Gastrointestinal",
                "quantity": 8,   # LOW STOCK (<= 30)
                "min_stock_level": 30,
                "price": 8.00,
                "expiry_date": today + timedelta(days=80),
                "supplier": "Torrent Pharma"
            },
            {
                "name": "Insulin Glargine 100 IU/ml",
                "batch_number": "BATCH-INS-2025-99",
                "category": "Antidiabetic",
                "quantity": 0,   # OUT OF STOCK!
                "min_stock_level": 15,
                "price": 540.00,
                "expiry_date": today + timedelta(days=120),
                "supplier": "BioCold Chain Distribution"
            },
            {
                "name": "Salbutamol Inhaler 100mcg",
                "batch_number": "BATCH-SLB-2026-30",
                "category": "Respiratory",
                "quantity": 32,
                "min_stock_level": 10,
                "price": 145.00,
                "expiry_date": today + timedelta(days=320),
                "supplier": "GlaxoSmithKline (GSK)"
            },
            {
                "name": "Ibuprofen 400mg",
                "batch_number": "BATCH-IBU-2025-33",
                "category": "Analgesics & Antipyretics",
                "quantity": 210,
                "min_stock_level": 40,
                "price": 3.20,
                "expiry_date": today - timedelta(days=20),  # EXPIRED!
                "supplier": "Abbott India"
            }
        ]

        for m_data in sample_medicines:
            med = Medicine(user_id=demo_user.id, **m_data)
            db.session.add(med)
            db.session.flush()

            # Add initial usage log sample
            usage = UsageLog(
                medicine_id=med.id,
                quantity_used=5,
                used_on=datetime.utcnow() - timedelta(days=2),
                note="Initial inventory reconciliation & prescription dispense"
            )
            db.session.add(usage)

        db.session.commit()
        print("[Database Setup] Default user created: admin@pharmacy.com (Password: admin123)")

        # Generate initial alerts for seeded data
        check_and_generate_alerts(app)
        print("[Database Setup] Initial alerts evaluated successfully.\n")

if __name__ == '__main__':
    # Initialize database tables and demo seed
    try:
        init_database_tables()
    except Exception as e:
        print(f"[Warning] Database initialization error: {e}")

    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    print("=" * 70)
    print(" Medicine Stock & Expiry Tracker - Cloud REST API Microservice")
    print(" Cloud Computing Academic Project (NIE Mysore - ISE)")
    print(f" Server running on: http://localhost:{port}")
    print(f" Default Demo Login: admin@pharmacy.com | admin123")
    print("=" * 70)

    app.run(host='0.0.0.0', port=port, debug=debug)
