import cv2
import threading
import time
import json
import numpy as np
import os
from datetime import datetime
from database import get_db
from ai_engine import ai_engine

class CameraStream:
    def __init__(self, camera_id, name, source_type, source_url, location, detection_mode, capacity_limit=10):
        self.camera_id = camera_id
        self.name = name
        self.source_type = source_type
        self.source_url = source_url
        self.location = location
        self.detection_mode = detection_mode # 'all', 'attendance_only', 'intruders', 'id_card', 'grooming', 'shoes', 'crowding', 'disabled'
        self.capacity_limit = capacity_limit
        
        self.cap = None
        self.running = False
        self.lock = threading.Lock()
        self.latest_jpeg = None
        self.latest_raw_frame = None
        self.thread = None
        
        # Load sample portrait for simulated feeds
        self.sim_portrait = None
        try:
            face_file = os.path.join(os.path.dirname(__file__), "static", "uploads", "faces", "651_1788261597.jpg")
            if os.path.exists(face_file):
                self.sim_portrait = cv2.imread(face_file)
        except Exception:
            pass
        
        # Cooldown trackers to prevent database spamming
        self.last_attendance_time = {} # student_id -> timestamp
        self.last_alert_time = {}      # alert_type -> timestamp
        self.latest_stats = {
            "faces_count": 0,
            "fps": 0,
            "status": "Initializing",
            "id_card_violations": 0,
            "haircut_violations": 0,
            "shoe_violations": 0
        }

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _open_capture(self):
        if self.source_type == "device":
            try:
                idx = int(self.source_url)
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]
                for backend in backends:
                    try:
                        cap = cv2.VideoCapture(idx, backend)
                        if cap is not None and cap.isOpened():
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            # Warm up sensor with a few reads
                            for _ in range(5):
                                ret, f = cap.read()
                                if ret and f is not None:
                                    print(f"[CameraStream] Camera device {idx} successfully opened with backend {backend}.")
                                    return cap
                                time.sleep(0.08)
                            cap.release()
                    except Exception:
                        pass
            except Exception as e:
                print(f"[CameraStream] Error opening device {self.source_url}: {e}")
        elif self.source_type == "ip":
            try:
                cap = cv2.VideoCapture(self.source_url)
                if cap.isOpened():
                    return cap
            except Exception as e:
                print(f"[CameraStream] Error opening IP stream {self.source_url}: {e}")
        return None

    def _generate_simulated_frame(self, frame_idx):
        """Generates dynamic surveillance feed with AI sensor visuals if physical webcam is offline."""
        w, h = 640, 420
        frame = np.full((h, w, 3), (16, 20, 26), dtype=np.uint8)
        
        # Perspective floor grid
        grid_color = (40, 50, 60)
        for i in range(1, 10):
            y = int(h * 0.42 + (i * i * h * 0.0055))
            cv2.line(frame, (0, y), (w, y), grid_color, 1)
        
        for i in range(-6, 7):
            cv2.line(frame, (w // 2 + i * 35, int(h * 0.42)), (w // 2 + i * 220, h), grid_color, 1)
        
        # Tech crosshair & ambient status
        cv2.putText(frame, f"FEED: {self.name.upper()}", (25, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (95, 227, 214), 1)
        cv2.putText(frame, f"ZONE: {self.location.upper()} | MODE: {self.detection_mode.upper()}", (25, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 160, 180), 1)
        cv2.putText(frame, "MULTI-MODAL SENSORS ONLINE // FACE + ID + HAIR + SHOES", (25, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 110, 130), 1)
        
        # Dynamic pulse radar
        pulse = int(abs(np.sin(frame_idx * 0.06)) * 45) + 30
        cv2.circle(frame, (w // 2, h // 2 + 40), pulse, (35, 55, 65), 1)
        cv2.circle(frame, (w // 2, h // 2 + 40), 4, (95, 227, 214), -1)
        
        # Simulated scanned target box & portrait
        sim_x = int(w // 2 - 45 + np.sin(frame_idx * 0.03) * 50)
        sim_y = int(h * 0.30)
        box_w, box_h = 90, 110
        if self.sim_portrait is not None:
            try:
                face_crop = cv2.resize(self.sim_portrait, (box_w, box_h))
                frame[sim_y:sim_y+box_h, sim_x:sim_x+box_w] = face_crop
            except Exception:
                pass
        cv2.rectangle(frame, (sim_x, sim_y), (sim_x + box_w, sim_y + box_h), (95, 227, 214), 1)
        cv2.putText(frame, "SIM SCAN: ID [OK] HAIR [REG] SHOES [WORN]", (sim_x - 30, sim_y + box_h + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (95, 227, 214), 1)
        
        return frame

    def _get_enrolled_students(self):
        """Fetch all students with enrolled face embeddings from SQLite."""
        try:
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
            return enrolled
        except Exception as e:
            print(f"[CameraStream] DB error fetching enrolled students: {e}")
            return []

    def _log_attendance(self, student_id, confidence, id_card_status, haircut_status, shoe_status, hair_length_ratio):
        now_ts = time.time()
        # Cooldown: log once every 3 minutes per student per camera
        if student_id in self.last_attendance_time:
            if now_ts - self.last_attendance_time[student_id] < 180:
                return
        
        self.last_attendance_time[student_id] = now_ts
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO attendance (student_id, camera_id, confidence, method, status, id_card_status, haircut_status, shoe_status, hair_length_ratio)
            VALUES (?, ?, ?, 'Face + Multi-Modal AI', 'Present', ?, ?, ?, ?)
            """, (student_id, self.camera_id, float(confidence), id_card_status, haircut_status, shoe_status, float(hair_length_ratio)))
            conn.commit()
            conn.close()
            print(f"[CameraStream] Logged attendance for student ID {student_id} (ID:{id_card_status}, Hair:{haircut_status}, Shoes:{shoe_status})")
        except Exception as e:
            print(f"[CameraStream] Error logging attendance: {e}")

    def _log_alert(self, alert_type, description, confidence, frame=None):
        now_ts = time.time()
        # Cooldown: log once every 40 seconds per alert type
        if alert_type in self.last_alert_time:
            if now_ts - self.last_alert_time[alert_type] < 40:
                return
        
        self.last_alert_time[alert_type] = now_ts
        
        snapshot_filename = None
        if frame is not None:
            try:
                alerts_dir = os.path.join(os.path.dirname(__file__), "static", "uploads", "alerts")
                os.makedirs(alerts_dir, exist_ok=True)
                snapshot_filename = f"alert_cam{self.camera_id}_{int(now_ts)}.jpg"
                save_path = os.path.join(alerts_dir, snapshot_filename)
                cv2.imwrite(save_path, frame)
            except Exception as e:
                print(f"[CameraStream] Snapshot save error: {e}")
                
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO alerts (camera_id, alert_type, description, confidence, snapshot_path, is_resolved)
            VALUES (?, ?, ?, ?, ?, 0)
            """, (self.camera_id, alert_type, description, float(confidence), snapshot_filename))
            conn.commit()
            conn.close()
            print(f"[CameraStream] Raised Alert [{alert_type}] on Camera {self.camera_id}: {description}")
        except Exception as e:
            print(f"[CameraStream] Error logging alert: {e}")

    def _run(self):
        self.cap = self._open_capture()
        frame_idx = 0
        last_fps_time = time.time()
        fps_count = 0
        
        enrolled_cache = self._get_enrolled_students()
        last_cache_update = time.time()

        consecutive_failures = 0
        while self.running:
            frame_idx += 1
            fps_count += 1
            now = time.time()
            if now - last_fps_time >= 1.0:
                self.latest_stats["fps"] = round(fps_count / (now - last_fps_time), 1)
                fps_count = 0
                last_fps_time = now

            if now - last_cache_update >= 5.0:
                enrolled_cache = self._get_enrolled_students()
                last_cache_update = now

            frame = None
            if self.cap and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if ret and raw_frame is not None:
                    frame = raw_frame
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures > 20:
                        print(f"[CameraStream] Camera {self.camera_id} signal lost. Reconnecting...")
                        self.cap.release()
                        time.sleep(0.5)
                        self.cap = self._open_capture()
                        consecutive_failures = 0
            elif self.cap is None and frame_idx % 60 == 0:
                # Periodic retry to open physical camera if offline
                self.cap = self._open_capture()

            if frame is None:
                frame = self._generate_simulated_frame(frame_idx)
                self.latest_stats["status"] = "Simulated / AI Feeds"
            else:
                self.latest_stats["status"] = "Active Live Stream"

            # Multi-Modal AI Detection (Face, ID Card, Haircut, Shoes)
            detections = []
            if self.detection_mode != "disabled":
                # Run full frame multi-modal inspection
                inspection = ai_engine.inspect_full_frame(frame, enrolled_cache)
                detections = inspection.get("detections", [])
                self.latest_stats["faces_count"] = len(detections)
                
                # Check Overcrowding
                if len(detections) > self.capacity_limit and self.detection_mode in ["all", "crowding"]:
                    desc = f"Capacity exceeded at {self.location}. Limit: {self.capacity_limit}, Current: {len(detections)} persons."
                    self._log_alert("Crowding", desc, 0.95, frame)

                # Process detections for compliance & attendance
                for det in detections:
                    face = det.get('face', {})
                    id_card = det.get('id_card', {})
                    haircut = det.get('haircut', {})
                    shoes = det.get('shoes', {})
                    
                    matched_student = face.get('student')
                    score = face.get('confidence', 0.0) / 100.0
                    
                    # 1. Attendance & Face Identification
                    if matched_student and self.detection_mode in ["all", "attendance_only"]:
                        id_status = "Detected" if id_card.get('detected') else "Missing"
                        hair_status = haircut.get('status', 'Short (Regulation)')
                        shoe_status = shoes.get('status', 'Shoes Worn')
                        ratio = haircut.get('hair_length_ratio', 0.25)
                        
                        self._log_attendance(
                            student_id=matched_student['id'],
                            confidence=score,
                            id_card_status=id_status,
                            haircut_status=hair_status,
                            shoe_status=shoe_status,
                            hair_length_ratio=ratio
                        )
                    
                    # 2. Alert: Unregistered Person
                    if not matched_student and self.detection_mode in ["all", "intruders"]:
                        desc = f"Unregistered individual detected in {self.location} zone."
                        self._log_alert("Unregistered Person", desc, 0.82, frame)
                    
                    # 3. Alert: Missing ID Card
                    if not id_card.get('detected') and self.detection_mode in ["all", "id_card"]:
                        target_name = matched_student['name'] if matched_student else "Individual"
                        desc = f"{target_name} spotted without required ID Card badge at {self.location}."
                        self._log_alert("Missing ID Card", desc, 0.90, frame)
                    
                    # 4. Alert: Haircut / Grooming Violation
                    if not haircut.get('compliant', True) and self.detection_mode in ["all", "grooming"]:
                        target_name = matched_student['name'] if matched_student else "Student"
                        desc = f"Grooming Alert: {target_name} exceeds regulation haircut length ({haircut.get('hair_length_ratio')} ratio) at {self.location}."
                        self._log_alert("Haircut Violation", desc, 0.86, frame)
                    
                    # 5. Alert: Shoe / Footwear Violation
                    if shoes.get('detected') is False and self.detection_mode in ["all", "shoes"]:
                        target_name = matched_student['name'] if matched_student else "Individual"
                        desc = f"Footwear Violation: {target_name} detected barefoot or wearing non-regulation slippers at {self.location}."
                        self._log_alert("Barefoot / Missing Shoes", desc, 0.89, frame)

            # Store raw unannotated frame for clean enrollment capture
            with self.lock:
                self.latest_raw_frame = frame.copy()

            # Render Cyberpunk AI HUD on the live stream
            hud_frame = ai_engine.draw_hud(frame, detections, camera_name=self.name, mode=self.detection_mode)
            
            # Encode JPEG
            ret, jpeg = cv2.imencode('.jpg', hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                with self.lock:
                    self.latest_jpeg = jpeg.tobytes()

            time.sleep(0.03)

    def get_jpeg(self):
        with self.lock:
            return self.latest_jpeg

    def get_raw_frame(self):
        with self.lock:
            return self.latest_raw_frame.copy() if self.latest_raw_frame is not None else None


class CameraManager:
    def __init__(self):
        self.streams = {}

    def detect_hardware_cameras(self):
        """Scans hardware indices on host machine to discover connected USB webcams."""
        available = []
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]
        for idx in range(6):
            found = False
            for backend in backends:
                if found:
                    break
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap is not None and cap.isOpened():
                        for _ in range(4):
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                available.append({
                                    "index": str(idx),
                                    "name": f"Webcam Device {idx} ({frame.shape[1]}x{frame.shape[0]})",
                                    "status": "Ready to Allot"
                                })
                                found = True
                                break
                            time.sleep(0.08)
                        cap.release()
                except Exception:
                    pass
        return available

    def sync_cameras(self):
        """Loads cameras from database and starts streams."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, source_type, source_url, location, status, detection_mode, capacity_limit FROM cameras")
            rows = cursor.fetchall()
            conn.close()

            current_ids = set()
            for r in rows:
                cid = r['id']
                current_ids.add(cid)
                if r['status'] == 'Active':
                    if cid not in self.streams:
                        stream = CameraStream(
                            camera_id=cid,
                            name=r['name'],
                            source_type=r['source_type'],
                            source_url=r['source_url'],
                            location=r['location'],
                            detection_mode=r['detection_mode'],
                            capacity_limit=r['capacity_limit']
                        )
                        stream.start()
                        self.streams[cid] = stream
                else:
                    if cid in self.streams:
                        self.streams[cid].stop()
                        del self.streams[cid]

            for cid in list(self.streams.keys()):
                if cid not in current_ids:
                    self.streams[cid].stop()
                    del self.streams[cid]
        except Exception as e:
            print(f"[CameraManager] Sync error: {e}")

    def get_stream(self, camera_id):
        return self.streams.get(camera_id)

    def restart_camera(self, camera_id):
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]
        self.sync_cameras()

    def shutdown(self):
        for s in self.streams.values():
            s.stop()
        self.streams.clear()

camera_manager = CameraManager()
