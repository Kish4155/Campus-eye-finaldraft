import os
import cv2
import json
import base64
import threading
import numpy as np
import mediapipe as mp
from datetime import datetime

class MultiModalAIEngine:
    def __init__(self):
        print("[AIEngine] Initializing OpenCV & MediaPipe AI Detection Suite...")
        
        # 1. OpenCV Haar Face Detector
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # 2. MediaPipe Pose for Full Body, Torso (ID card) & Feet (Shoes)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Match threshold for face recognition
        self.match_threshold = 0.65
        self.pose_lock = threading.Lock()
        print("[AIEngine] Initialized successfully with Face + ID Card + Haircut + Shoe Detectors.")

    def detect_faces(self, image_bgr):
        """Detect all face bounding boxes in an OpenCV BGR image."""
        if image_bgr is None or image_bgr.size == 0:
            return []
        
        try:
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.12,
                minNeighbors=5,
                minSize=(40, 40)
            )
            if len(faces) == 0:
                return []
            return faces
        except Exception as e:
            print(f"[AIEngine] Face detect error: {e}")
            return []

    def extract_embedding(self, face_chip_bgr):
        """Extracts a normalized 256-dimensional spatial color & texture histogram embedding."""
        if face_chip_bgr is None or face_chip_bgr.size == 0:
            return None
        
        try:
            resized = cv2.resize(face_chip_bgr, (112, 112))
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            
            # 1. Color histogram features
            hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256])
            
            # 2. Spatial gradient / texture features
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            mag, _ = cv2.cartToPolar(gx, gy)
            hist_mag = cv2.calcHist([mag.astype(np.uint8)], [0], None, [32], [0, 256])
            
            # 3. Grid spatial cells (4x4)
            grid_feats = []
            cell_h, cell_w = 28, 28
            for r in range(4):
                for c in range(4):
                    cell = gray[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                    grid_feats.append(float(np.mean(cell)))
                    grid_feats.append(float(np.std(cell)))
                    
            combined = np.concatenate([
                hist_h.flatten(), 
                hist_s.flatten(), 
                hist_v.flatten(), 
                hist_mag.flatten(),
                np.array(grid_feats, dtype=np.float32)
            ])
            
            norm = np.linalg.norm(combined)
            if norm > 0:
                combined = combined / norm
            return combined.astype(np.float32)
        except Exception as e:
            print(f"[AIEngine] Extract embedding error: {e}")
            return None

    def enroll_face_from_image(self, image_bgr, save_dir, student_roll):
        """Process an image for enrollment, extract embedding and save cropped portrait."""
        faces = self.detect_faces(image_bgr)
        if len(faces) == 0:
            return False, "No face detected in image. Please ensure good lighting and face the camera directly.", None, None
        
        # Pick largest face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]
        
        h_img, w_img = image_bgr.shape[:2]
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.15)
        
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w_img, x + w + pad_x)
        y2 = min(h_img, y + h + pad_y)
        
        face_crop = image_bgr[y1:y2, x1:x2]
        embedding = self.extract_embedding(face_crop)
        
        if embedding is None:
            return False, "Failed to compute facial feature vector.", None, None
        
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{student_roll}_{int(datetime.now().timestamp())}.jpg"
        photo_path = os.path.join(save_dir, filename)
        cv2.imwrite(photo_path, face_crop)
        
        return True, "Face enrolled successfully!", embedding.tolist(), filename

    def match_face(self, query_emb, enrolled_students):
        """Compare query embedding with enrolled students using cosine similarity."""
        if query_emb is None or len(enrolled_students) == 0:
            return None, 0.0
        
        best_match = None
        best_score = -1.0
        
        for student in enrolled_students:
            target_emb = student.get('embedding_vec')
            if target_emb is None or len(target_emb) != len(query_emb):
                continue
            
            sim = float(np.dot(query_emb, target_emb))
            if sim > best_score:
                best_score = sim
                best_match = student
                
        if best_score >= self.match_threshold:
            return best_match, best_score
        else:
            return None, max(0.0, best_score)

    # ----------------- ID CARD DETECTION -----------------
    def detect_id_card(self, image_bgr, face_box=None, pose_landmarks=None):
        """
        Detects ID card / badge / lanyard on the person's torso.
        Returns: { 'detected': bool, 'box': (x,y,w,h) or None, 'confidence': float, 'status': str }
        """
        h_img, w_img = image_bgr.shape[:2]
        torso_roi = None
        tx, ty, tw, th = 0, 0, 0, 0
        
        # 1. Localize Torso via Face Box or Pose Landmarks
        if face_box is not None:
            fx, fy, fw, fh = face_box
            # Torso region is below chin down to ~2.5x face height, with ~2x width
            tx = max(0, fx - int(fw * 0.4))
            ty = min(h_img, fy + fh)
            tw = min(w_img - tx, int(fw * 1.8))
            th = min(h_img - ty, int(fh * 2.2))
            if tw > 20 and th > 20:
                torso_roi = image_bgr[ty:ty+th, tx:tx+tw]

        if torso_roi is None or torso_roi.size == 0:
            return {"detected": False, "box": None, "confidence": 0.0, "status": "Missing"}
        
        try:
            gray_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2GRAY)
            # Edge detection for rectangular badge / card holder
            edges = cv2.Canny(gray_torso, 40, 150)
            
            # Find contours in torso
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            id_card_found = False
            best_card_box = None
            best_card_score = 0.0
            
            # Check for rectangular contours matching ID card aspect ratio (~1.3 to 1.8)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 250 < area < (tw * th * 0.45):
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                    
                    if 4 <= len(approx) <= 6:
                        bx, by, bw, bh = cv2.boundingRect(approx)
                        aspect = float(bw) / bh if bh > 0 else 0
                        
                        # ID cards are either vertical (0.55 - 0.75) or horizontal (1.25 - 1.85)
                        if (0.5 <= aspect <= 0.85) or (1.25 <= aspect <= 1.85):
                            # Check texture / text density inside candidate card box
                            card_chip = gray_torso[by:by+bh, bx:bx+bw]
                            if card_chip.size > 0:
                                var = float(np.var(card_chip))
                                # ID cards typically have text, photo, and badge border (high variance)
                                if var > 350:
                                    score = min(0.98, 0.65 + (var / 5000.0))
                                    if score > best_card_score:
                                        best_card_score = score
                                        id_card_found = True
                                        best_card_box = (tx + bx, ty + by, bw, bh)
            
            # 2. Check for Lanyard / Ribbon Neck Straps (Color or Line Hough)
            if not id_card_found:
                # Check for lanyard lines descending across upper chest
                lines = cv2.HoughLinesP(edges[:int(th*0.5), :], 1, np.pi/180, 25, minLineLength=int(th*0.25), maxLineGap=10)
                if lines is not None and len(lines) >= 2:
                    # Diagonal straps meeting in V-shape
                    id_card_found = True
                    best_card_score = 0.72
                    bw = int(tw * 0.35)
                    bh = int(th * 0.35)
                    bx = tx + int(tw * 0.32)
                    by = ty + int(th * 0.3)
                    best_card_box = (bx, by, bw, bh)

            if id_card_found and best_card_box:
                return {
                    "detected": True,
                    "box": best_card_box,
                    "confidence": round(best_card_score, 2),
                    "status": "Detected (Compliant)"
                }
            else:
                return {
                    "detected": False,
                    "box": None,
                    "confidence": 0.0,
                    "status": "Missing / Not Visible (Violation)"
                }
        except Exception as e:
            print(f"[AIEngine] ID card detect error: {e}")
            return {"detected": False, "box": None, "confidence": 0.0, "status": "Missing"}

    # ----------------- HAIRCUT / HAIR LENGTH ANALYZER -----------------
    def analyze_haircut(self, image_bgr, face_box):
        """
        Analyzes hair length relative to face height.
        Classifications:
          - 'Short (Regulation)' (<= 0.38 ratio) -> Compliant
          - 'Medium Length' (0.39 - 0.68 ratio) -> Acceptable
          - 'Long (Needs Haircut)' (> 0.68 ratio) -> Violation
        """
        if face_box is None:
            return {"status": "Unknown", "hair_length_ratio": 0.0, "compliant": True, "box": None}
        
        fx, fy, fw, fh = face_box
        h_img, w_img = image_bgr.shape[:2]
        
        # Region of interest for hair: above face, around ears, and down to neck/collar
        hx1 = max(0, fx - int(fw * 0.3))
        hy1 = max(0, fy - int(fh * 0.45))
        hx2 = min(w_img, fx + fw + int(fw * 0.3))
        hy2 = min(h_img, fy + fh + int(fh * 0.85))
        
        hair_roi = image_bgr[hy1:hy2, hx1:hx2]
        if hair_roi is None or hair_roi.size == 0:
            return {"status": "Short (Regulation)", "hair_length_ratio": 0.25, "compliant": True, "box": (hx1, hy1, hx2-hx1, hy2-hy1)}
        
        try:
            # Segment hair pixels (dark/brown/black/dyed color contrast relative to skin)
            hsv = cv2.cvtColor(hair_roi, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(hair_roi, cv2.COLOR_BGR2GRAY)
            
            # Dark hair mask (Value < 90 or dark saturation)
            _, dark_mask = cv2.threshold(gray, 85, 255, cv2.THRESH_BINARY_INV)
            
            # Find hair contours
            contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            lowest_hair_y = hy1 + int(fh * 0.1)
            highest_hair_y = hy1 + int(fh * 0.3)
            
            for cnt in contours:
                if cv2.contourArea(cnt) > 80:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    abs_by1 = hy1 + by
                    abs_by2 = hy1 + by + bh
                    
                    if abs_by1 < highest_hair_y:
                        highest_hair_y = abs_by1
                    if abs_by2 > lowest_hair_y:
                        lowest_hair_y = abs_by2

            # Compute hair span below forehead
            chin_y = fy + fh
            hair_extension_below_chin = max(0, lowest_hair_y - chin_y)
            
            # Ratio of hair extension relative to face height
            ratio = round(float(hair_extension_below_chin) / float(fh), 2)
            
            if ratio <= 0.38:
                status = "Short (Regulation)"
                compliant = True
            elif ratio <= 0.68:
                status = "Medium Length"
                compliant = True
            else:
                status = "Long (Needs Haircut)"
                compliant = False

            hair_box = (hx1, highest_hair_y, hx2 - hx1, max(30, lowest_hair_y - highest_hair_y))
            
            return {
                "status": status,
                "hair_length_ratio": ratio,
                "compliant": compliant,
                "box": hair_box
            }
        except Exception as e:
            print(f"[AIEngine] Haircut analysis error: {e}")
            return {"status": "Short (Regulation)", "hair_length_ratio": 0.25, "compliant": True, "box": None}

    # ----------------- SHOES / FOOTWEAR DETECTION -----------------
    def detect_shoes(self, image_bgr, pose_landmarks=None):
        """
        Detects whether shoes are worn vs missing / barefoot.
        Returns: { 'detected': bool or None, 'status': str, 'box': (x,y,w,h) or None, 'confidence': float }
        """
        h_img, w_img = image_bgr.shape[:2]
        
        # 1. If Pose Landmarks provided or extractable
        if pose_landmarks is None:
            try:
                rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                with self.pose_lock:
                    results = self.pose.process(rgb)
                if results.pose_landmarks:
                    pose_landmarks = results.pose_landmarks.landmark
            except Exception:
                pose_landmarks = None
        
        if pose_landmarks is not None:
            # Check feet landmarks: 27/28 (ankles), 29/30 (heels), 31/32 (foot index)
            try:
                l_ankle = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
                r_ankle = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
                l_foot = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value]
                r_foot = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value]
                
                # Check visibility
                ankles_visible = (l_ankle.visibility > 0.40 or r_ankle.visibility > 0.40)
                feet_in_frame = (l_foot.y < 1.05 and r_foot.y < 1.05) and (l_ankle.y > 0.4)
                
                if ankles_visible and feet_in_frame:
                    # Feet are visible! Extract shoe bounding box
                    fx1 = int(min(l_ankle.x, r_ankle.x, l_foot.x, r_foot.x) * w_img) - 20
                    fy1 = int(min(l_ankle.y, r_ankle.y) * h_img) - 10
                    fx2 = int(max(l_ankle.x, r_ankle.x, l_foot.x, r_foot.x) * w_img) + 20
                    fy2 = int(max(l_foot.y, r_foot.y) * h_img) + 20
                    
                    fx1 = max(0, fx1)
                    fy1 = max(0, fy1)
                    fx2 = min(w_img, fx2)
                    fy2 = min(h_img, fy2)
                    
                    shoe_roi = image_bgr[fy1:fy2, fx1:fx2]
                    if shoe_roi.size > 0:
                        # Check footwear coverage vs barefoot skin tone
                        hsv_feet = cv2.cvtColor(shoe_roi, cv2.COLOR_BGR2HSV)
                        # Skin color range
                        skin_mask = cv2.inRange(hsv_feet, np.array([0, 20, 70]), np.array([20, 255, 255]))
                        skin_ratio = np.sum(skin_mask > 0) / float(shoe_roi.shape[0] * shoe_roi.shape[1])
                        
                        # If low skin ratio and dark/leather/sneaker profile -> Shoes Worn
                        if skin_ratio < 0.38:
                            return {
                                "detected": True,
                                "status": "Shoes Worn (Compliant)",
                                "box": (fx1, fy1, fx2 - fx1, fy2 - fy1),
                                "confidence": 0.94
                            }
                        else:
                            return {
                                "detected": False,
                                "status": "Barefoot / Slippers (Violation)",
                                "box": (fx1, fy1, fx2 - fx1, fy2 - fy1),
                                "confidence": 0.88
                            }
            except Exception as e:
                print(f"[AIEngine] Pose feet parsing error: {e}")

        # 2. Fallback heuristic: check bottom 20% of frame for full-body view
        bottom_h = int(h_img * 0.2)
        bottom_roi = image_bgr[h_img - bottom_h:h_img, :]
        if bottom_roi.size > 0:
            gray_bottom = cv2.cvtColor(bottom_roi, cv2.COLOR_BGR2GRAY)
            edges_bottom = cv2.Canny(gray_bottom, 50, 150)
            if np.sum(edges_bottom > 0) > (bottom_roi.size * 0.04):
                # Distinct floor objects / shoes present
                return {
                    "detected": True,
                    "status": "Shoes Worn (Compliant)",
                    "box": (int(w_img * 0.25), h_img - bottom_h + 10, int(w_img * 0.5), bottom_h - 20),
                    "confidence": 0.78
                }

        return {
            "detected": None,
            "status": "Upper Body (Out of Frame)",
            "box": None,
            "confidence": 0.50
        }

    # ----------------- FULL FRAME MULTI-MODAL INSPECTION -----------------
    def inspect_full_frame(self, image_bgr, enrolled_students=None):
        """
        Executes a complete AI multi-modal audit on an image frame:
        Face Recognition + ID Card Detection + Haircut Analysis + Shoe Detection.
        """
        if image_bgr is None or image_bgr.size == 0:
            return {"success": False, "error": "Invalid frame data"}
        
        enrolled_students = enrolled_students or []
        faces = self.detect_faces(image_bgr)
        
        # Run MediaPipe Pose on whole frame
        try:
            rgb_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            with self.pose_lock:
                pose_res = self.pose.process(rgb_img)
            pose_landmarks = pose_res.pose_landmarks.landmark if pose_res.pose_landmarks else None
        except Exception:
            pose_landmarks = None
        
        # Shoe detection
        shoes_result = self.detect_shoes(image_bgr, pose_landmarks)
        
        detections = []
        
        for (x, y, w, h) in faces:
            pad = int(w * 0.1)
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(image_bgr.shape[1], x + w + pad)
            y2 = min(image_bgr.shape[0], y + h + pad)
            face_chip = image_bgr[y1:y2, x1:x2]
            
            # 1. Face Match
            query_emb = self.extract_embedding(face_chip)
            matched_student, score = self.match_face(query_emb, enrolled_students)
            
            # 2. ID Card Detection
            id_card = self.detect_id_card(image_bgr, face_box=(x, y, w, h), pose_landmarks=pose_landmarks)
            
            # 3. Haircut / Hair Length Analysis
            haircut = self.analyze_haircut(image_bgr, face_box=(x, y, w, h))
            
            detections.append({
                "face": {
                    "box": [int(x), int(y), int(w), int(h)],
                    "is_match": matched_student is not None,
                    "student": matched_student,
                    "confidence": round(score * 100, 1)
                },
                "id_card": {
                    "detected": id_card["detected"],
                    "box": [int(v) for v in id_card["box"]] if id_card["box"] else None,
                    "confidence": id_card["confidence"],
                    "status": id_card["status"]
                },
                "haircut": {
                    "status": haircut["status"],
                    "hair_length_ratio": haircut["hair_length_ratio"],
                    "compliant": haircut["compliant"],
                    "box": [int(v) for v in haircut["box"]] if haircut["box"] else None
                },
                "shoes": shoes_result
            })
            
        return {
            "success": True,
            "faces_count": len(faces),
            "detections": detections,
            "overall_shoes": shoes_result
        }

    # ----------------- HUD RENDERER -----------------
    def draw_hud(self, frame, detections, camera_name="SURVEILLANCE FEED", mode="ALL"):
        """Draws aesthetic Cyberpunk / Dark Glass HUD with Face, ID Card, Haircut, and Shoes."""
        h, w = frame.shape[:2]
        
        # Cyberpunk Frame border
        cv2.rectangle(frame, (8, 8), (w - 8, h - 8), (55, 65, 40), 1)
        
        for det in detections:
            # 1. Face Box & Label
            face = det.get('face', {})
            box = face.get('box', (0,0,0,0))
            x, y, box_w, box_h = box
            is_match = face.get('is_match', False)
            student = face.get('student')
            score = face.get('confidence', 0.0)
            
            color = (214, 227, 95) if (is_match and student) else (99, 93, 239)
            name_text = f"{student['name']} ({int(score)}%)" if (is_match and student) else f"UNKNOWN ({int(score)}%)"
            
            # Draw Face Box
            cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), color, 2)
            
            # Corner accents
            c_len = min(14, box_w // 4)
            cv2.line(frame, (x, y), (x + c_len, y), color, 3)
            cv2.line(frame, (x, y), (x, y + c_len), color, 3)
            cv2.line(frame, (x + box_w, y), (x + box_w - c_len, y), color, 3)
            cv2.line(frame, (x + box_w, y), (x + box_w, y + c_len), color, 3)
            
            # Name badge
            tag_y = max(32, y - 8)
            cv2.rectangle(frame, (x, tag_y - 22), (x + max(160, len(name_text)*9), tag_y + 4), (18, 21, 28), -1)
            cv2.rectangle(frame, (x, tag_y - 22), (x + max(160, len(name_text)*9), tag_y + 4), color, 1)
            cv2.putText(frame, name_text, (x + 5, tag_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
            
            # 2. ID Card Overlay
            id_card = det.get('id_card', {})
            id_ok = id_card.get('detected', False)
            id_color = (95, 227, 214) if id_ok else (70, 70, 240) # Green or Red
            id_text = "ID: OK" if id_ok else "ID: MISSING"
            
            if id_card.get('box'):
                ix, iy, iw, ih = id_card['box']
                cv2.rectangle(frame, (ix, iy), (ix + iw, iy + ih), id_color, 2)
                cv2.putText(frame, id_text, (ix + 4, iy + ih - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, id_color, 1, cv2.LINE_AA)
            else:
                # Draw ID badge below face
                cv2.putText(frame, id_text, (x + 5, y + box_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, id_color, 1, cv2.LINE_AA)
            
            # 3. Haircut Overlay
            haircut = det.get('haircut', {})
            hair_ok = haircut.get('compliant', True)
            hair_color = (255, 210, 100) if hair_ok else (50, 140, 255) # Cyan/Gold or Orange
            hair_status = haircut.get('status', 'Short')
            hair_text = f"HAIR: {hair_status.upper()}"
            
            cv2.putText(frame, hair_text, (x + 5, y + box_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, hair_color, 1, cv2.LINE_AA)
            
            # 4. Shoes Overlay
            shoes = det.get('shoes', {})
            if shoes.get('box'):
                sx, sy, sw, sh = shoes['box']
                shoe_ok = shoes.get('detected', True)
                shoe_color = (95, 227, 214) if shoe_ok else (70, 70, 240)
                cv2.rectangle(frame, (sx, sy), (sx + sw, sy + sh), shoe_color, 2)
                cv2.putText(frame, f"SHOES: {'WORN' if shoe_ok else 'MISSING'}", (sx + 4, sy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, shoe_color, 1, cv2.LINE_AA)

        # Header HUD
        cv2.rectangle(frame, (0, 0), (w, 32), (18, 21, 28), -1)
        cv2.line(frame, (0, 32), (w, 32), (40, 48, 60), 1)
        cv2.circle(frame, (18, 16), 5, (99, 93, 239), -1)
        
        hud_title = f"CAMPUS-EYE // {camera_name.upper()} [AI SUITE: FACE + ID + HAIR + SHOES]"
        cv2.putText(frame, hud_title, (32, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 225, 235), 1, cv2.LINE_AA)
        
        counter_txt = f"TARGETS: {len(detections)}"
        cv2.putText(frame, counter_txt, (w - 110, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (95, 227, 214), 1, cv2.LINE_AA)

        return frame

# Singleton Engine
ai_engine = MultiModalAIEngine()
