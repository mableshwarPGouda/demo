from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from datetime import datetime, date, timedelta
import io
import csv
import os
import platform
from database import get_db_connection, init_db, seed_sample_data

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

# Determine CORS origins from environment variable
frontend_env = os.getenv("FRONTEND_URL", "*")
cors_origins = [o.strip() for o in frontend_env.split(",") if o.strip()] if frontend_env != "*" and frontend_env else "*"

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")
# Enable CORS for all routes (allows React frontend on any port/domain to communicate)
CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=(cors_origins != "*"))

# Initialize database on startup
init_db()
seed_sample_data()

START_TIME = datetime.now()

def enrich_medicine(row):
    """Adds calculated fields such as days until expiry, expiry status, and stock status."""
    med = dict(row)
    today = date.today()
    try:
        exp_date = datetime.strptime(med["expiry_date"], "%Y-%m-%d").date()
        days_remaining = (exp_date - today).days
    except Exception:
        days_remaining = 9999

    med["days_to_expiry"] = days_remaining

    if days_remaining < 0:
        med["expiry_status"] = "expired"
        med["expiry_badge_label"] = f"Expired {abs(days_remaining)}d ago"
        med["expiry_severity"] = "critical"
    elif days_remaining <= 30:
        med["expiry_status"] = "expiring_soon"
        med["expiry_badge_label"] = f"Expires in {days_remaining}d"
        med["expiry_severity"] = "danger"
    elif days_remaining <= 60:
        med["expiry_status"] = "expiring_warning"
        med["expiry_badge_label"] = f"Expires in {days_remaining}d"
        med["expiry_severity"] = "warning"
    else:
        med["expiry_status"] = "good"
        med["expiry_badge_label"] = f"{days_remaining}d remaining"
        med["expiry_severity"] = "safe"

    qty = med["quantity"]
    threshold = med["min_threshold"]
    if qty == 0:
        med["stock_status"] = "out_of_stock"
        med["stock_badge_label"] = "Out of Stock"
        med["stock_severity"] = "critical"
    elif qty <= threshold:
        med["stock_status"] = "low_stock"
        med["stock_badge_label"] = f"Low Stock ({qty}/{threshold})"
        med["stock_severity"] = "warning"
    else:
        med["stock_status"] = "in_stock"
        med["stock_badge_label"] = "In Stock"
        med["stock_severity"] = "safe"

    med["total_value"] = round(med["quantity"] * med["unit_price"], 2)
    return med

@app.route("/api/health", methods=["GET"])
def health_check():
    """Cloud Health Check endpoint reporting uptime, OS, and cloud status."""
    uptime_seconds = int((datetime.now() - START_TIME).total_seconds())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM medicines")
    med_count = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "status": "healthy",
        "service": "Medicine Stock & Expiry Tracker Cloud API",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "environment": os.environ.get("FLASK_ENV", "cloud-production"),
        "platform": platform.platform(),
        "database": "SQLite (Cloud SQL / MySQL Ready)",
        "total_medicines_cached": med_count,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Aggregated metrics and KPIs for the inventory dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    rows = cursor.fetchall()
    medicines = [enrich_medicine(r) for r in rows]

    total_medicines = len(medicines)
    total_units = sum(m["quantity"] for m in medicines)
    total_inventory_value = round(sum(m["total_value"] for m in medicines), 2)

    expired_count = sum(1 for m in medicines if m["expiry_status"] == "expired")
    expiring_soon_count = sum(1 for m in medicines if m["expiry_status"] == "expiring_soon")
    expiring_warning_count = sum(1 for m in medicines if m["expiry_status"] == "expiring_warning")
    low_stock_count = sum(1 for m in medicines if m["stock_status"] == "low_stock")
    out_of_stock_count = sum(1 for m in medicines if m["stock_status"] == "out_of_stock")

    # Category Breakdown
    cat_map = {}
    for m in medicines:
        cat = m["category"]
        if cat not in cat_map:
            cat_map[cat] = {"category": cat, "count": 0, "units": 0, "value": 0.0}
        cat_map[cat]["count"] += 1
        cat_map[cat]["units"] += m["quantity"]
        cat_map[cat]["value"] = round(cat_map[cat]["value"] + m["total_value"], 2)
    category_breakdown = sorted(list(cat_map.values()), key=lambda x: x["value"], reverse=True)

    # Expiry Distribution breakdown
    expiry_distribution = [
        {"name": "Expired", "count": expired_count, "color": "#ef4444"},
        {"name": "Expiring <30d", "count": expiring_soon_count, "color": "#f97316"},
        {"name": "Expiring 30-60d", "count": expiring_warning_count, "color": "#eab308"},
        {"name": "Safe (>60d)", "count": total_medicines - (expired_count + expiring_soon_count + expiring_warning_count), "color": "#10b981"}
    ]

    # Recent transactions
    cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 5")
    recent_transactions = [dict(t) for t in cursor.fetchall()]

    conn.close()

    return jsonify({
        "total_medicines": total_medicines,
        "total_units": total_units,
        "total_inventory_value": total_inventory_value,
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
        "expiring_warning_count": expiring_warning_count,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "category_breakdown": category_breakdown,
        "expiry_distribution": expiry_distribution,
        "recent_transactions": recent_transactions
    })

@app.route("/api/medicines", methods=["GET"])
def get_medicines():
    """Retrieve list of medicines with search, category filtering, and status filtering."""
    search = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip() # expired, expiring_soon, safe
    stock_status = request.args.get("stock_status", "").strip() # out_of_stock, low_stock, in_stock
    sort_by = request.args.get("sort_by", "name").strip()
    sort_order = request.args.get("sort_order", "asc").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    rows = cursor.fetchall()
    conn.close()

    enriched = [enrich_medicine(r) for r in rows]

    # Filters
    filtered = []
    for m in enriched:
        if search:
            match = (
                search in m["name"].lower() or
                search in (m["generic_name"] or "").lower() or
                search in m["batch_number"].lower() or
                search in (m["manufacturer"] or "").lower() or
                search in (m["storage_location"] or "").lower()
            )
            if not match:
                continue

        if category and m["category"] != category:
            continue

        if status:
            if status == "expired" and m["expiry_status"] != "expired":
                continue
            elif status == "expiring_soon" and m["expiry_status"] not in ("expiring_soon", "expiring_warning"):
                continue
            elif status == "safe" and m["expiry_status"] != "good":
                continue

        if stock_status and m["stock_status"] != stock_status:
            continue

        filtered.append(m)

    # Sorting
    reverse = (sort_order.lower() == "desc")
    if sort_by == "name":
        filtered.sort(key=lambda x: x["name"].lower(), reverse=reverse)
    elif sort_by == "expiry_date":
        filtered.sort(key=lambda x: x["expiry_date"], reverse=reverse)
    elif sort_by == "quantity":
        filtered.sort(key=lambda x: x["quantity"], reverse=reverse)
    elif sort_by == "unit_price":
        filtered.sort(key=lambda x: x["unit_price"], reverse=reverse)
    elif sort_by == "total_value":
        filtered.sort(key=lambda x: x["total_value"], reverse=reverse)
    else:
        filtered.sort(key=lambda x: x["id"], reverse=reverse)

    return jsonify({"count": len(filtered), "medicines": filtered})

@app.route("/api/medicines/<int:med_id>", methods=["GET"])
def get_medicine(med_id):
    """Retrieve details and audit logs for a single medicine."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Medicine not found"}), 404

    med = enrich_medicine(row)
    cursor.execute("SELECT * FROM transactions WHERE medicine_id = ? ORDER BY id DESC", (med_id,))
    transactions = [dict(t) for t in cursor.fetchall()]
    conn.close()

    med["transactions"] = transactions
    return jsonify(med)

@app.route("/api/medicines", methods=["POST"])
def add_medicine():
    """Add a new medicine to inventory."""
    data = request.get_json() or {}
    required = ["name", "batch_number", "category", "expiry_date"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check batch uniqueness
    cursor.execute("SELECT id FROM medicines WHERE batch_number = ?", (data["batch_number"].strip(),))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"Batch number '{data['batch_number']}' already exists"}), 409

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quantity = int(data.get("quantity", 0))

    cursor.execute("""
    INSERT INTO medicines (
        name, generic_name, batch_number, category, dosage_form,
        manufacturer, supplier, quantity, min_threshold, unit_price,
        mfg_date, expiry_date, storage_location, prescription_required,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"].strip(),
        data.get("generic_name", "").strip(),
        data["batch_number"].strip(),
        data["category"].strip(),
        data.get("dosage_form", "Tablet"),
        data.get("manufacturer", "").strip(),
        data.get("supplier", "").strip(),
        quantity,
        int(data.get("min_threshold", 15)),
        float(data.get("unit_price", 0.0)),
        data.get("mfg_date") or None,
        data["expiry_date"].strip(),
        data.get("storage_location", "General Shelf").strip(),
        1 if data.get("prescription_required") else 0,
        now_str, now_str
    ))
    new_id = cursor.lastrowid

    # Log initial inventory transaction
    cursor.execute("""
    INSERT INTO transactions (
        medicine_id, medicine_name, batch_number, type,
        quantity_change, resulting_quantity, reason, performed_by, timestamp
    ) VALUES (?, ?, ?, 'INITIAL', ?, ?, 'Added to Inventory', 'Staff Pharmacist', ?)
    """, (new_id, data["name"].strip(), data["batch_number"].strip(), quantity, quantity, now_str))

    conn.commit()

    cursor.execute("SELECT * FROM medicines WHERE id = ?", (new_id,))
    created = enrich_medicine(cursor.fetchone())
    conn.close()

    return jsonify({"message": "Medicine added successfully", "medicine": created}), 201

@app.route("/api/medicines/<int:med_id>", methods=["PUT"])
def update_medicine(med_id):
    """Update medicine details."""
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        return jsonify({"error": "Medicine not found"}), 404

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_quantity = int(data.get("quantity", current["quantity"]))

    cursor.execute("""
    UPDATE medicines SET
        name = ?,
        generic_name = ?,
        category = ?,
        dosage_form = ?,
        manufacturer = ?,
        supplier = ?,
        quantity = ?,
        min_threshold = ?,
        unit_price = ?,
        mfg_date = ?,
        expiry_date = ?,
        storage_location = ?,
        prescription_required = ?,
        updated_at = ?
    WHERE id = ?
    """, (
        data.get("name", current["name"]).strip(),
        data.get("generic_name", current["generic_name"]),
        data.get("category", current["category"]).strip(),
        data.get("dosage_form", current["dosage_form"]),
        data.get("manufacturer", current["manufacturer"]),
        data.get("supplier", current["supplier"]),
        new_quantity,
        int(data.get("min_threshold", current["min_threshold"])),
        float(data.get("unit_price", current["unit_price"])),
        data.get("mfg_date", current["mfg_date"]),
        data.get("expiry_date", current["expiry_date"]).strip(),
        data.get("storage_location", current["storage_location"]),
        1 if data.get("prescription_required", current["prescription_required"]) else 0,
        now_str,
        med_id
    ))

    # Audit transaction if quantity was manually altered
    if new_quantity != current["quantity"]:
        delta = new_quantity - current["quantity"]
        cursor.execute("""
        INSERT INTO transactions (
            medicine_id, medicine_name, batch_number, type,
            quantity_change, resulting_quantity, reason, performed_by, timestamp
        ) VALUES (?, ?, ?, 'ADJUSTMENT', ?, ?, 'Manual Inventory Adjustment', 'Staff Pharmacist', ?)
        """, (med_id, current["name"], current["batch_number"], delta, new_quantity, now_str))

    conn.commit()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    updated = enrich_medicine(cursor.fetchone())
    conn.close()

    return jsonify({"message": "Medicine updated successfully", "medicine": updated})

@app.route("/api/medicines/<int:med_id>", methods=["DELETE"])
def delete_medicine(med_id):
    """Remove a medicine from inventory."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, batch_number FROM medicines WHERE id = ?", (med_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Medicine not found"}), 404

    cursor.execute("DELETE FROM medicines WHERE id = ?", (med_id,))
    cursor.execute("DELETE FROM transactions WHERE medicine_id = ?", (med_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": f"Medicine '{row['name']}' deleted successfully"})

@app.route("/api/medicines/<int:med_id>/dispense", methods=["POST"])
def dispense_medicine(med_id):
    """Dispense medicine (decrement stock) with reason and audit log."""
    data = request.get_json() or {}
    amount = int(data.get("amount", 0))
    reason = data.get("reason", "Patient Dispense / Prescription Sale")
    dispensed_to = data.get("dispensed_to", "Patient Outpatient")

    if amount <= 0:
        return jsonify({"error": "Dispense amount must be greater than zero"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    med = cursor.fetchone()
    if not med:
        conn.close()
        return jsonify({"error": "Medicine not found"}), 404

    if med["quantity"] < amount:
        conn.close()
        return jsonify({"error": f"Insufficient stock. Available: {med['quantity']}, Requested: {amount}"}), 400

    new_quantity = med["quantity"] - amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("UPDATE medicines SET quantity = ?, updated_at = ? WHERE id = ?", (new_quantity, now_str, med_id))
    cursor.execute("""
    INSERT INTO transactions (
        medicine_id, medicine_name, batch_number, type,
        quantity_change, resulting_quantity, reason, performed_by, timestamp
    ) VALUES (?, ?, ?, 'DISPENSE', ?, ?, ?, ?, ?)
    """, (med_id, med["name"], med["batch_number"], -amount, new_quantity, f"{reason} ({dispensed_to})", "Staff Pharmacist", now_str))

    conn.commit()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    updated = enrich_medicine(cursor.fetchone())
    conn.close()

    return jsonify({"message": f"Dispensed {amount} units successfully", "medicine": updated})

@app.route("/api/medicines/<int:med_id>/restock", methods=["POST"])
def restock_medicine(med_id):
    """Restock medicine (increment stock) with purchase order / supplier invoice."""
    data = request.get_json() or {}
    amount = int(data.get("amount", 0))
    reason = data.get("reason", "Supplier Restock Shipment")
    po_number = data.get("po_number", "PO-AUTO")

    if amount <= 0:
        return jsonify({"error": "Restock amount must be greater than zero"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    med = cursor.fetchone()
    if not med:
        conn.close()
        return jsonify({"error": "Medicine not found"}), 404

    new_quantity = med["quantity"] + amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("UPDATE medicines SET quantity = ?, updated_at = ? WHERE id = ?", (new_quantity, now_str, med_id))
    cursor.execute("""
    INSERT INTO transactions (
        medicine_id, medicine_name, batch_number, type,
        quantity_change, resulting_quantity, reason, performed_by, timestamp
    ) VALUES (?, ?, ?, 'RESTOCK', ?, ?, ?, ?, ?)
    """, (med_id, med["name"], med["batch_number"], amount, new_quantity, f"{reason} [Ref: {po_number}]", "Inventory Manager", now_str))

    conn.commit()
    cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
    updated = enrich_medicine(cursor.fetchone())
    conn.close()

    return jsonify({"message": f"Restocked {amount} units successfully", "medicine": updated})

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Generates real-time active alerts for expired, expiring, and low stock medicines."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    rows = cursor.fetchall()
    conn.close()

    medicines = [enrich_medicine(r) for r in rows]
    alerts = []

    for m in medicines:
        # Expired alert
        if m["expiry_status"] == "expired":
            alerts.append({
                "id": f"exp-past-{m['id']}",
                "medicine_id": m["id"],
                "medicine_name": m["name"],
                "batch_number": m["batch_number"],
                "type": "EXPIRED",
                "severity": "critical",
                "title": f"EXPIRED: {m['name']}",
                "message": f"Batch {m['batch_number']} expired on {m['expiry_date']} ({abs(m['days_to_expiry'])} days ago). Quarantine immediately to prevent dispensing.",
                "action_recommended": "Isolate in Quarantine & Schedule Disposal",
                "location": m["storage_location"],
                "date": m["expiry_date"]
            })
        elif m["expiry_status"] == "expiring_soon":
            alerts.append({
                "id": f"exp-soon-{m['id']}",
                "medicine_id": m["id"],
                "medicine_name": m["name"],
                "batch_number": m["batch_number"],
                "type": "EXPIRING_SOON",
                "severity": "danger",
                "title": f"Expiring Soon: {m['name']}",
                "message": f"Batch {m['batch_number']} will expire in {m['days_to_expiry']} days ({m['expiry_date']}). Prioritize for First-Expiry-First-Out (FEFO) dispensing.",
                "action_recommended": "Prioritize FEFO Dispensing / Notify Doctor",
                "location": m["storage_location"],
                "date": m["expiry_date"]
            })

        # Stock alerts
        if m["stock_status"] == "out_of_stock":
            alerts.append({
                "id": f"stock-out-{m['id']}",
                "medicine_id": m["id"],
                "medicine_name": m["name"],
                "batch_number": m["batch_number"],
                "type": "OUT_OF_STOCK",
                "severity": "critical",
                "title": f"Stock Out: {m['name']}",
                "message": f"Stock depleted (0 units). Reorder threshold is {m['min_threshold']} units.",
                "action_recommended": "Urgent Purchase Order Required",
                "location": m["storage_location"],
                "date": m["expiry_date"]
            })
        elif m["stock_status"] == "low_stock":
            alerts.append({
                "id": f"stock-low-{m['id']}",
                "medicine_id": m["id"],
                "medicine_name": m["name"],
                "batch_number": m["batch_number"],
                "type": "LOW_STOCK",
                "severity": "warning",
                "title": f"Low Stock Warning: {m['name']}",
                "message": f"Only {m['quantity']} units left in stock. Reorder threshold is {m['min_threshold']} units.",
                "action_recommended": "Create Restock Order",
                "location": m["storage_location"],
                "date": m["expiry_date"]
            })

    # Sort alerts: critical first, then danger, then warning
    severity_order = {"critical": 0, "danger": 1, "warning": 2, "info": 3}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 9))

    return jsonify({
        "count": len(alerts),
        "alerts": alerts
    })

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """Retrieve all transaction audit logs."""
    limit = int(request.args.get("limit", 50))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/export", methods=["GET"])
def export_data():
    """Export inventory to CSV or JSON format."""
    format_type = request.args.get("format", "csv").lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    enriched = [enrich_medicine(r) for r in rows]

    if format_type == "json":
        return jsonify(enriched)

    # Default CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Generic Name", "Batch Number", "Category", "Dosage Form",
        "Manufacturer", "Supplier", "Quantity", "Min Threshold", "Unit Price",
        "Total Value", "Mfg Date", "Expiry Date", "Days To Expiry", "Expiry Status",
        "Stock Status", "Storage Location"
    ])

    for m in enriched:
        writer.writerow([
            m["id"], m["name"], m.get("generic_name", ""), m["batch_number"],
            m["category"], m["dosage_form"], m.get("manufacturer", ""),
            m.get("supplier", ""), m["quantity"], m["min_threshold"],
            m["unit_price"], m["total_value"], m.get("mfg_date", ""),
            m["expiry_date"], m["days_to_expiry"], m["expiry_status"],
            m["stock_status"], m["storage_location"]
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"medicine_inventory_{date.today().isoformat()}.csv"
    )

@app.route("/api/reset-data", methods=["POST"])
def reset_data():
    """Reset database to initial demo dataset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS medicines")
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS notifications")
    conn.commit()
    conn.close()

    init_db()
    seed_sample_data()

    return jsonify({"message": "Database reset to sample medicines successfully"})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serves the unified single-page React app and static assets directly from Flask."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Medicine Stock & Expiry Tracker API on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
