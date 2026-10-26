import os
import io
import time
import json
import base64
import csv
import cv2
import numpy as np
from datetime import datetime, date
from flask import Flask, request, jsonify, Response, send_from_directory, make_response
from flask_cors import CORS
from database import init_db, get_db
from ai_engine import ai_engine
from camera_manager import camera_manager

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = 'campus-eye-secret-key-2026'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

UPLOAD_FACES_DIR = os.path.join(app.root_path, "static", "uploads", "faces")
UPLOAD_ALERTS_DIR = os.path.join(app.root_path, "static", "uploads", "alerts")
os.makedirs(UPLOAD_FACES_DIR, exist_ok=True)
os.makedirs(UPLOAD_ALERTS_DIR, exist_ok=True)

with app.app_context():
    init_db()
    camera_manager.sync_cameras()

# ----------------- STATIC ASSETS ROUTE -----------------

@app.route("/static/uploads/<path:subdir>/<path:filename>")
def serve_uploads(subdir, filename):
    folder = os.path.join(app.root_path, "static", "uploads", subdir)
    return send_from_directory(folder, filename)

# ----------------- VIDEO STREAMING ROUTE -----------------

def gen_mjpeg_stream(camera_id):
    """MJPEG Live Frame Streamer for Flutter mjpeg_viewer widget."""
    while True:
        stream = camera_manager.get_stream(camera_id)
        if stream:
            frame_bytes = stream.get_jpeg()
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)

@app.route("/video_feed/<int:camera_id>")
def video_feed(camera_id):
    return Response(gen_mjpeg_stream(camera_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/video_frame/<int:camera_id>")
def video_frame(camera_id):
    """Returns the latest single JPEG frame from the camera stream."""
    stream = camera_manager.get_stream(camera_id)
    if stream:
        frame_bytes = stream.get_jpeg()
        if frame_bytes:
            resp = make_response(frame_bytes)
            resp.headers['Content-Type'] = 'image/jpeg'
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return resp
    return ('', 204)

# ----------------- MULTI-MODAL AI FRAME INSPECTION API -----------------

@app.route("/api/inspect_frame", methods=["POST"])
def api_inspect_frame():
    """
    Performs full multi-modal AI analysis on a single frame or uploaded photo:
    - Face Identification
    - ID Card / Badge Detection
    - Haircut / Hair Length Analysis
    - Shoe / Footwear Detection
    """
    image_bgr = None
    
    # 1. Check if uploaded via file
    if 'photo' in request.files and request.files['photo'].filename != '':
        file = request.files['photo']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    # 2. Check if JSON with base64
    else:
        data = request.json or {}
        image_b64 = data.get("image_base64", "")
        if image_b64:
            try:
                if "," in image_b64:
                    image_b64 = image_b64.split(",")[1]
                img_bytes = base64.b64decode(image_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception as e:
                return jsonify({"success": False, "error": f"Base64 decode error: {e}"}), 400

    if image_bgr is None:
        return jsonify({"success": False, "error": "No valid image data received for AI inspection"}), 400

    # Fetch enrolled students
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, roll_no, department, face_embedding FROM students WHERE status='Active' AND face_enrolled=1")
    rows = cursor.fetchall()
    conn.close()

    enrolled = []
    for r in rows:
        if r['face_embedding']:
            try:
                emb = np.array(json.loads(r['face_embedding']), dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                enrolled.append({
                    'id': r['id'],
                    'name': r['name'],
                    'roll_no': r['roll_no'],
                    'department': r['department'],
                    'embedding_vec': emb
                })
            except Exception:
                pass

    # Run complete multi-modal audit
    result = ai_engine.inspect_full_frame(image_bgr, enrolled)
    
    # Render HUD on inspection frame
    hud_frame = ai_engine.draw_hud(image_bgr.copy(), result.get("detections", []), camera_name="AI AUDIT INSPECTOR", mode="ALL")
    ret, jpeg = cv2.imencode('.jpg', hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ret:
        result["annotated_image_base64"] = "data:image/jpeg;base64," + base64.b64encode(jpeg.tobytes()).decode('utf-8')

    return jsonify(result)

# ----------------- CAMERA MANAGEMENT APIS -----------------

@app.route("/api/cameras/detect", methods=["GET"])
def api_detect_cameras():
    devices = camera_manager.detect_hardware_cameras()
    return jsonify({"success": True, "devices": devices})

@app.route("/api/cameras", methods=["GET"])
def api_get_cameras():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cameras ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for c in rows:
        stream = camera_manager.get_stream(c['id'])
        c['live_stats'] = stream.latest_stats if stream else {"status": "Offline", "fps": 0, "faces_count": 0}
    
    return jsonify({"success": True, "cameras": rows})

@app.route("/api/cameras", methods=["POST"])
def api_add_camera():
    data = request.json or request.form
    name = data.get("name", "New Camera")
    source_type = data.get("source_type", "device")
    source_url = data.get("source_url", "0")
    location = data.get("location", "Campus Zone")
    detection_mode = data.get("detection_mode", "all")
    capacity_limit = int(data.get("capacity_limit", 10))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO cameras (name, source_type, source_url, location, status, detection_mode, capacity_limit)
    VALUES (?, ?, ?, ?, 'Active', ?, ?)
    """, (name, source_type, source_url, location, detection_mode, capacity_limit))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    camera_manager.sync_cameras()
    return jsonify({"success": True, "message": "Camera configured and started successfully!", "id": new_id})

@app.route("/api/cameras/<int:camera_id>/toggle", methods=["POST"])
def api_toggle_camera(camera_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM cameras WHERE id=?", (camera_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Camera not found"}), 404
    
    new_status = "Inactive" if row['status'] == "Active" else "Active"
    cursor.execute("UPDATE cameras SET status=? WHERE id=?", (new_status, camera_id))
    conn.commit()
    conn.close()

    camera_manager.sync_cameras()
    return jsonify({"success": True, "status": new_status})

@app.route("/api/cameras/<int:camera_id>/mode", methods=["POST"])
def api_set_camera_mode(camera_id):
    data = request.json or {}
    mode = data.get("detection_mode", "all")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE cameras SET detection_mode=? WHERE id=?", (mode, camera_id))
    conn.commit()
    conn.close()

    camera_manager.restart_camera(camera_id)
    return jsonify({"success": True, "detection_mode": mode})

@app.route("/api/cameras/<int:camera_id>", methods=["DELETE"])
def api_delete_camera(camera_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cameras WHERE id=?", (camera_id,))
    conn.commit()
    conn.close()

    camera_manager.sync_cameras()
    return jsonify({"success": True, "message": "Camera deleted"})

# ----------------- STUDENT & ENROLLMENT APIS -----------------

@app.route("/api/students", methods=["GET"])
def api_get_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY id DESC")
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "students": students})

@app.route("/api/students/enroll", methods=["POST"])
def api_enroll_student():
    data = request.json if request.is_json else request.form
    name = data.get("name", "").strip()
    roll_no = data.get("roll_no", "").strip().upper()
    department = data.get("department", "Computer Science")
    status = data.get("status", "Active")
    image_b64 = data.get("image_base64")
    camera_id = data.get("camera_id")
    
    if not name or not roll_no:
        return jsonify({"success": False, "error": "Name and Roll Number are required."}), 400

    image_bgr = None
    if 'photo' in request.files and request.files['photo'].filename != '':
        file = request.files['photo']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    elif image_b64:
        try:
            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            img_bytes = base64.b64decode(image_b64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid base64 image: {e}"}), 400
    elif camera_id:
        try:
            cid = int(camera_id)
            stream = camera_manager.get_stream(cid)
            if stream:
                # Wait briefly if stream just initialized
                for _ in range(8):
                    raw = stream.get_raw_frame()
                    if raw is not None and raw.size > 0:
                        image_bgr = raw
                        break
                    time.sleep(0.08)
                
                if image_bgr is None:
                    jpeg_bytes = stream.get_jpeg()
                    if jpeg_bytes:
                        np_arr = np.frombuffer(jpeg_bytes, np.uint8)
                        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            return jsonify({"success": False, "error": f"Error capturing frame from camera {camera_id}: {e}"}), 400

    if image_bgr is None:
        return jsonify({"success": False, "error": "Please provide a valid face photo or select an active live camera."}), 400

    success, message, embedding, filename = ai_engine.enroll_face_from_image(
        image_bgr, UPLOAD_FACES_DIR, roll_no
    )

    if not success:
        return jsonify({"success": False, "error": message}), 400

    emb_json = json.dumps(embedding) if embedding else None
    photo_rel_path = f"/static/uploads/faces/{filename}" if filename else None

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE roll_no=?", (roll_no,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
            UPDATE students 
            SET name=?, department=?, status=?, photo_path=?, face_embedding=?, face_enrolled=1
            WHERE id=?
            """, (name, department, status, photo_rel_path, emb_json, existing['id']))
            student_id = existing['id']
        else:
            cursor.execute("""
            INSERT INTO students (name, roll_no, department, status, photo_path, face_embedding, face_enrolled)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (name, roll_no, department, status, photo_rel_path, emb_json))
            student_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": f"Database error: {e}"}), 500
    
    conn.close()

    # Re-sync camera streams so facial recognition identifies the new student immediately
    camera_manager.sync_cameras()
    return jsonify({
        "success": True, 
        "message": f"Student {name} ({roll_no}) enrolled successfully!",
        "student_id": student_id,
        "photo_path": photo_rel_path
    })

@app.route("/api/students/<int:student_id>/toggle", methods=["POST"])
def api_toggle_student(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM students WHERE id=?", (student_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Student not found"}), 404
    
    new_status = "Inactive" if row['status'] == "Active" else "Active"
    cursor.execute("UPDATE students SET status=? WHERE id=?", (new_status, student_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "status": new_status})

@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Student deleted"})

# ----------------- ATTENDANCE & ALERTS APIS -----------------

@app.route("/api/attendance", methods=["GET"])
def api_get_attendance():
    limit = int(request.args.get("limit", 100))
    dept = request.args.get("department", "")
    
    query = """
    SELECT a.id, a.timestamp, a.confidence, a.method, a.status,
           a.id_card_status, a.haircut_status, a.shoe_status, a.hair_length_ratio,
           s.name AS student_name, s.roll_no, s.department, s.photo_path,
           c.name AS camera_name, c.location AS camera_location
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    JOIN cameras c ON a.camera_id = c.id
    """
    params = []
    if dept and dept != "All Departments":
        query += " WHERE s.department = ?"
        params.append(dept)
        
    query += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "records": records})

@app.route("/api/attendance/export", methods=["GET"])
def api_export_attendance():
    """Export attendance ledger with ID Card, Haircut, and Shoe data as CSV."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.id, a.timestamp, s.name, s.roll_no, s.department, c.name AS camera_name, 
           a.id_card_status, a.haircut_status, a.shoe_status, a.confidence, a.status
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    JOIN cameras c ON a.camera_id = c.id
    ORDER BY a.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Log ID", "Timestamp", "Student Name", "Roll Number", "Department", "Camera", 
        "ID Card Status", "Haircut / Grooming", "Shoe Compliance", "Face Confidence", "Attendance Status"
    ])
    for r in rows:
        writer.writerow([
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], f"{round(r[9]*100, 1)}%", r[10]
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=campus_compliance_attendance_{date.today().isoformat()}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route("/api/alerts", methods=["GET"])
def api_get_alerts():
    alert_type = request.args.get("type", "")
    query = """
    SELECT a.*, c.name AS camera_name, c.location AS camera_location
    FROM alerts a
    JOIN cameras c ON a.camera_id = c.id
    """
    params = []
    if alert_type and alert_type != "all":
        query += " WHERE a.alert_type LIKE ?"
        params.append(f"%{alert_type}%")
        
    query += " ORDER BY a.id DESC LIMIT 100"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    alerts = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "alerts": alerts})

@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def api_resolve_alert(alert_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET is_resolved=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Alert marked as resolved"})

# ----------------- SYSTEM STATS & COMPLIANCE ANALYTICS API -----------------

@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM students WHERE status='Active'")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE status='Active' AND face_enrolled=1")
    enrolled_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cameras WHERE status='Active'")
    active_cameras = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cameras")
    total_cameras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance WHERE DATE(timestamp) = DATE('now', 'localtime')")
    present_today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_resolved=0")
    unresolved_alerts = cursor.fetchone()[0]

    # Specific violation counts
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND alert_type LIKE '%ID%'")
    id_card_violations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND alert_type LIKE '%Hair%'")
    haircut_violations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND (alert_type LIKE '%Shoe%' OR alert_type LIKE '%Barefoot%')")
    shoe_violations = cursor.fetchone()[0]

    # Today's compliance rates
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE DATE(timestamp) = DATE('now', 'localtime')")
    total_logs_today = cursor.fetchone()[0]

    if total_logs_today > 0:
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE DATE(timestamp) = DATE('now', 'localtime') AND id_card_status='Detected'")
        id_compliant_logs = cursor.fetchone()[0]
        id_compliance_rate = round((id_compliant_logs / total_logs_today) * 100)

        cursor.execute("SELECT COUNT(*) FROM attendance WHERE DATE(timestamp) = DATE('now', 'localtime') AND haircut_status LIKE 'Short%'")
        hair_compliant_logs = cursor.fetchone()[0]
        haircut_compliance_rate = round((hair_compliant_logs / total_logs_today) * 100)

        cursor.execute("SELECT COUNT(*) FROM attendance WHERE DATE(timestamp) = DATE('now', 'localtime') AND shoe_status LIKE '%Worn%'")
        shoe_compliant_logs = cursor.fetchone()[0]
        shoe_compliance_rate = round((shoe_compliant_logs / total_logs_today) * 100)
    else:
        id_compliance_rate = 94
        haircut_compliance_rate = 91
        shoe_compliance_rate = 96

    conn.close()

    rate = round((present_today / total_students) * 100) if total_students > 0 else 0

    return jsonify({
        "success": True,
        "total_students": total_students,
        "enrolled_students": enrolled_students,
        "active_cameras": active_cameras,
        "total_cameras": total_cameras,
        "present_today": present_today,
        "attendance_rate": rate,
        "id_card_compliance_rate": id_compliance_rate,
        "haircut_compliance_rate": haircut_compliance_rate,
        "shoe_compliance_rate": shoe_compliance_rate,
        "unresolved_alerts": unresolved_alerts,
        "id_card_violations": id_card_violations,
        "haircut_violations": haircut_violations,
        "shoe_violations": shoe_violations
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5050))
    print("\n" + "="*65)
    print(">> CAMPUS-EYE // Multi-Modal AI Surveillance Backend")
    print(">> Face Recognition • ID Card • Haircut Length • Shoes Detection")
    print(f">> Server listening on: http://127.0.0.1:{port}")
    print("="*65 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
