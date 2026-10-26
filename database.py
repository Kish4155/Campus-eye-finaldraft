import sqlite3
import json
import numpy as np
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campus_eye.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.join(os.path.dirname(__file__), "static", "uploads", "faces"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "static", "uploads", "alerts"), exist_ok=True)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_no TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        photo_path TEXT,
        face_embedding TEXT,
        face_enrolled INTEGER DEFAULT 0,
        id_card_status TEXT DEFAULT 'Compliant',
        haircut_status TEXT DEFAULT 'Short (Regulation)',
        shoe_status TEXT DEFAULT 'Shoes Worn',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Cameras table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_type TEXT DEFAULT 'device', -- 'device', 'ip', 'simulated'
        source_url TEXT NOT NULL, -- '0', '1', 'rtsp://...', 'sim_gate'
        location TEXT NOT NULL,
        status TEXT DEFAULT 'Active', -- 'Active', 'Inactive'
        detection_mode TEXT DEFAULT 'all', -- 'all', 'attendance_only', 'intruders', 'id_card', 'grooming', 'shoes', 'crowding'
        capacity_limit INTEGER DEFAULT 10,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Attendance & Multi-Modal Compliance Ledger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        camera_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        confidence REAL DEFAULT 0.0,
        method TEXT DEFAULT 'Face + Multi-Modal AI',
        status TEXT DEFAULT 'Present',
        id_card_status TEXT DEFAULT 'Detected',
        haircut_status TEXT DEFAULT 'Short (Regulation)',
        shoe_status TEXT DEFAULT 'Shoes Worn',
        hair_length_ratio REAL DEFAULT 0.25,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
    )
    """)
    
    # Security & Compliance Alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        alert_type TEXT NOT NULL, -- 'Missing ID Card', 'Haircut Violation', 'Barefoot / Missing Shoes', 'Unregistered Person', 'Crowding'
        description TEXT NOT NULL,
        confidence REAL DEFAULT 0.0,
        snapshot_path TEXT,
        is_resolved INTEGER DEFAULT 0,
        FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    
    # Check if columns exist in existing DB (for migrations)
    cursor.execute("PRAGMA table_info(attendance)")
    att_cols = [r[1] for r in cursor.fetchall()]
    if 'id_card_status' not in att_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN id_card_status TEXT DEFAULT 'Detected'")
    if 'haircut_status' not in att_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN haircut_status TEXT DEFAULT 'Short (Regulation)'")
    if 'shoe_status' not in att_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN shoe_status TEXT DEFAULT 'Shoes Worn'")
    if 'hair_length_ratio' not in att_cols:
        cursor.execute("ALTER TABLE attendance ADD COLUMN hair_length_ratio REAL DEFAULT 0.25")

    cursor.execute("PRAGMA table_info(students)")
    stu_cols = [r[1] for r in cursor.fetchall()]
    if 'id_card_status' not in stu_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN id_card_status TEXT DEFAULT 'Compliant'")
    if 'haircut_status' not in stu_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN haircut_status TEXT DEFAULT 'Short (Regulation)'")
    if 'shoe_status' not in stu_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN shoe_status TEXT DEFAULT 'Shoes Worn'")

    conn.commit()

    # Seed sample cameras if empty
    cursor.execute("SELECT COUNT(*) FROM cameras")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO cameras (name, source_type, source_url, location, status, detection_mode, capacity_limit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Main Campus Gate Alpha", "device", "0", "Campus Main Entrance & Turnstiles", "Active", "all", 20),
            ("Academic Block A Corridor", "simulated", "sim_corridor", "Corridor Alpha - Level 1", "Active", "all", 15),
            ("Room 101 AI Lab", "simulated", "sim_classroom", "Room 101 Computer Science Lab", "Active", "id_card", 8),
            ("Library Central Entry", "simulated", "sim_library", "Central Library Checkpoint", "Active", "all", 12),
            ("Auditorium North Wing", "simulated", "sim_auditorium", "Main Auditorium Hallway", "Active", "crowding", 25)
        ])
        conn.commit()
        
    # Seed sample students if empty
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO students (name, roll_no, department, status, face_enrolled, id_card_status, haircut_status, shoe_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Aarav Sharma", "CS2026001", "Computer Science & Eng", "Active", 0, "Compliant", "Short (Regulation)", "Shoes Worn"),
            ("Diya Patel", "CS2026002", "Computer Science & Eng", "Active", 0, "Compliant", "Medium Length", "Shoes Worn"),
            ("Rohan Gupta", "EE2026012", "Electrical Engineering", "Active", 0, "Missing", "Long (Needs Haircut)", "Shoes Worn"),
            ("Ananya Iyer", "ME2026045", "Mechanical Engineering", "Active", 0, "Compliant", "Medium Length", "Shoes Worn"),
            ("Kabir Mehta", "CS2026008", "Computer Science & Eng", "Active", 0, "Compliant", "Short (Regulation)", "Barefoot / Slippers"),
            ("Ishita Sen", "EC2026024", "Electronics & Comm", "Active", 0, "Compliant", "Short (Regulation)", "Shoes Worn"),
            ("Neha Verma", "CE2026055", "Civil Engineering", "Inactive", 0, "Compliant", "Short (Regulation)", "Shoes Worn")
        ])
        conn.commit()

    # Seed sample compliance alerts if empty
    cursor.execute("SELECT COUNT(*) FROM alerts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO alerts (camera_id, alert_type, description, confidence, is_resolved)
        VALUES (?, ?, ?, ?, ?)
        """, [
            (1, "Missing ID Card", "Student detected without visible ID card or lanyard badge at Main Gate.", 0.92, 0),
            (2, "Haircut Violation", "Grooming standard violation: Hair length exceeds regulation threshold (0.78 ratio).", 0.88, 0),
            (1, "Barefoot / Missing Shoes", "Footwear violation detected at Campus Main Entrance.", 0.91, 0),
            (3, "Unregistered Person", "Unrecognized person detected entering Room 101 AI Lab.", 0.85, 0)
        ])
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
