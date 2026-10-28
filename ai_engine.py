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

    # ----------------- ID CARD & LANYARD DETECTION -----------------
    def detect_id_card(self, image_bgr, face_box=None, pose_landmarks=None):
        """
        Detects ID card badge and lanyard on the person's torso with strict geometric
        and visual verification.
        
        Evaluates strap angles, collar origin positions, downward convergence near the neck/chest,
        and corroborates with rectangular ID badge geometry & text texture to prevent false positives
        from clothing folds, collar lines, seams, or buttons.
        
        Returns: { 'detected': bool, 'box': (x,y,w,h) or None, 'confidence': float, 'status': str, 'details': dict }
        """
        if image_bgr is None or image_bgr.size == 0 or face_box is None:
            return {
                "detected": False,
                "box": None,
                "confidence": 0.0,
                "status": "Missing / Not Visible (Violation)",
                "details": {"has_lanyard": False, "has_badge": False}
            }
        
        h_img, w_img = image_bgr.shape[:2]
        fx, fy, fw, fh = face_box
        
        # 1. Torso & Anatomical Anchors
        fc_x = fx + fw / 2.0
        chin_y = fy + fh
        
        neck_x = fc_x
        neck_y = chin_y
        shoulder_w = fw * 2.0
        
        # Utilize MediaPipe Pose landmarks if available for anatomical precision
        if pose_landmarks is not None:
            try:
                nose = pose_landmarks[self.mp_pose.PoseLandmark.NOSE.value]
                nose_px_x = nose.x * w_img
                nose_px_y = nose.y * h_img
                # Verify that pose landmarks match this specific face box
                if (fx - 0.25 * fw <= nose_px_x <= fx + 1.25 * fw) and (fy - 0.25 * fh <= nose_px_y <= fy + 1.25 * fh):
                    l_sh = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
                    r_sh = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
                    if l_sh.visibility > 0.30 and r_sh.visibility > 0.30:
                        r_sh_x = r_sh.x * w_img  # screen left (person's right)
                        l_sh_x = l_sh.x * w_img  # screen right (person's left)
                        sh_y = (l_sh.y + r_sh.y) * 0.5 * h_img
                        neck_x = (r_sh_x + l_sh_x) * 0.5
                        neck_y = min(chin_y, sh_y - 0.08 * fh)
                        shoulder_w = max(fw * 1.6, abs(l_sh_x - r_sh_x))
            except Exception as e:
                pass
                
        # Torso bounding box
        tx = max(0, int(neck_x - shoulder_w * 0.55))
        ty = max(0, int(neck_y))
        tw = min(w_img - tx, int(shoulder_w * 1.1))
        th = min(h_img - ty, int(fh * 2.5))
        
        if tw < 30 or th < 30:
            return {
                "detected": False,
                "box": None,
                "confidence": 0.0,
                "status": "Missing / Not Visible (Violation)",
                "details": {"has_lanyard": False, "has_badge": False}
            }
            
        try:
            torso_roi = image_bgr[ty:ty+th, tx:tx+tw]
            gray_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2GRAY)
            cx_rel = neck_x - tx  # Torso centerline in local ROI coordinates
            
            # 2. Multi-Channel Edge Detection
            # Captures colored lanyard straps (red, blue, green, black, white) against any clothing color
            smooth_b = cv2.GaussianBlur(torso_roi[:, :, 0], (5, 5), 1.2)
            smooth_g = cv2.GaussianBlur(torso_roi[:, :, 1], (5, 5), 1.2)
            smooth_r = cv2.GaussianBlur(torso_roi[:, :, 2], (5, 5), 1.2)
            smooth_gray = cv2.GaussianBlur(gray_torso, (5, 5), 1.2)
            
            e_b = cv2.Canny(smooth_b, 35, 110)
            e_g = cv2.Canny(smooth_g, 35, 110)
            e_r = cv2.Canny(smooth_r, 35, 110)
            e_gray = cv2.Canny(smooth_gray, 35, 110)
            
            edges_torso = cv2.bitwise_or(cv2.bitwise_or(e_b, e_g), cv2.bitwise_or(e_r, e_gray))
            
            # 3. Lanyard Strap Detection & Strict Geometric Verification
            upper_th = int(th * 0.70)
            lines = cv2.HoughLinesP(
                edges_torso[:upper_th, :],
                rho=1,
                theta=np.pi / 180,
                threshold=20,
                minLineLength=max(18, int(fh * 0.22)),
                maxLineGap=max(6, int(fh * 0.08))
            )
            
            left_straps = []   # Straps originating on screen-left (person's right side of neck)
            right_straps = []  # Straps originating on screen-right (person's left side of neck)
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if y1 > y2:
                        x1, y1, x2, y2 = x2, y2, x1, y1
                        
                    dy = y2 - y1
                    dx = x2 - x1
                    length = np.hypot(dx, dy)
                    if dy <= 0:
                        continue
                        
                    angle_from_vertical = np.degrees(np.arctan2(abs(dx), dy))
                    
                    # Rule A (Angle): Angle must be predominantly vertical or diagonal inwards (<= 38 degrees)
                    # Rejects horizontal or near-horizontal collar edges, pocket seams, stripes, folds
                    if angle_from_vertical > 38.0:
                        continue
                        
                    # Rule B (Position): Upper origin MUST be at the collar/neck (top 30% of torso ROI)
                    if y1 > int(th * 0.30):
                        continue
                        
                    # Rule C (Screen-Left Strap Candidate):
                    # MUST originate strictly to the LEFT of the neck centerline (lx1 <= cx_rel - 0.04*fw)
                    # MUST slope inwards to the right (dx >= 0) or hang nearly straight down (dx >= -0.06*dy)
                    if x1 <= cx_rel - 0.04 * fw and dx >= -0.06 * dy:
                        left_straps.append({
                            "pt1": (x1, y1), "pt2": (x2, y2),
                            "angle": angle_from_vertical, "slope": dx / float(dy),
                            "len": length
                        })
                        
                    # Rule D (Screen-Right Strap Candidate):
                    # MUST originate strictly to the RIGHT of the neck centerline (rx1 >= cx_rel + 0.04*fw)
                    # MUST slope inwards to the left (dx <= 0) or hang nearly straight down (dx <= 0.06*dy)
                    if x1 >= cx_rel + 0.04 * fw and dx <= 0.06 * dy:
                        right_straps.append({
                            "pt1": (x1, y1), "pt2": (x2, y2),
                            "angle": angle_from_vertical, "slope": dx / float(dy),
                            "len": length
                        })

            # Find matching (left_strap, right_strap) pair meeting near neck/chest
            best_lanyard = None
            best_lanyard_score = 0.0
            
            for l_st in left_straps:
                for r_st in right_straps:
                    lx1, ly1 = l_st["pt1"]
                    lx2, ly2 = l_st["pt2"]
                    rx1, ry1 = r_st["pt1"]
                    rx2, ry2 = r_st["pt2"]
                    
                    # 1. Top Separation: Straps must straddle the neck with realistic collar width
                    top_sep = rx1 - lx1
                    if not (0.28 * fw <= top_sep <= 1.6 * fw):
                        continue
                        
                    # 2. Upper points must both originate near the collar height
                    if abs(ly1 - ry1) > max(28, 0.35 * fh):
                        continue
                        
                    # 3. Downward Convergence: bottom separation must narrow towards midline
                    bottom_sep = rx2 - lx2
                    if bottom_sep >= top_sep:
                        continue
                    if bottom_sep > (0.35 * fw):
                        continue
                        
                    mL = l_st["slope"]
                    mR = r_st["slope"]
                    
                    # Opposing slopes: left slopes right (mL >= -0.06), right slopes left (mR <= 0.06)
                    # They must be converging: mL - mR > 0.05
                    if (mL - mR) < 0.05:
                        continue
                        
                    # Meeting point intersection
                    y_meet = ((rx1 - mR * ry1) - (lx1 - mL * ly1)) / (mL - mR)
                    x_meet = lx1 + mL * (y_meet - ly1)
                    
                    # Convergence point must be on the chest below collar
                    if not (int(fh * 0.22) <= y_meet <= int(th * 0.90)):
                        continue
                        
                    # Convergence point must be near the torso centerline
                    if abs(x_meet - cx_rel) > (0.30 * fw):
                        continue
                        
                    # Angle symmetry check
                    angle_diff = abs(l_st["angle"] - r_st["angle"])
                    if angle_diff > 22.0:
                        continue
                        
                    score = 0.72 + min(0.18, (l_st["len"] + r_st["len"]) / (fh * 2.0)) - (angle_diff / 100.0)
                    if score > best_lanyard_score:
                        best_lanyard_score = score
                        best_lanyard = {
                            "left": l_st,
                            "right": r_st,
                            "meet": (int(x_meet), int(y_meet)),
                            "score": score
                        }

            # 4. Rectangular ID Card Badge Detection
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed_edges = cv2.morphologyEx(edges_torso, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            best_card = None
            best_card_score = 0.0
            
            min_cw = int(fw * 0.18)
            max_cw = int(fw * 0.85)
            min_ch = int(fh * 0.22)
            max_ch = int(fh * 1.20)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 550 or area > (tw * th * 0.35):
                    continue
                    
                bx, by, bw, bh = cv2.boundingRect(cnt)
                if not (min_cw <= bw <= max_cw and min_ch <= bh <= max_ch):
                    continue
                    
                aspect = float(bw) / bh if bh > 0 else 0
                is_portrait = (0.46 <= aspect <= 0.88)
                is_landscape = (1.15 <= aspect <= 1.90)
                if not (is_portrait or is_landscape):
                    continue
                    
                card_cx = bx + bw / 2.0
                if abs(card_cx - cx_rel) > (0.55 * fw):
                    continue
                if by < int(fh * 0.15) or (by + bh) > int(th * 0.98):
                    continue
                    
                rect_fill = float(area) / (bw * bh)
                if rect_fill < 0.62:
                    continue
                    
                card_roi = gray_torso[by:by+bh, bx:bx+bw]
                if card_roi.size == 0:
                    continue
                    
                var = float(np.var(card_roi))
                if var < 300:
                    continue
                    
                # Text/photo ID cards have dense horizontal gradients
                sob_x = cv2.Sobel(card_roi, cv2.CV_32F, 1, 0, ksize=3)
                mean_grad = float(np.mean(np.abs(sob_x)))
                if mean_grad < 12.0:
                    continue
                    
                # Contrast with surrounding background
                pad = 8
                sy1 = max(0, by - pad)
                sy2 = min(th, by + bh + pad)
                sx1 = max(0, bx - pad)
                sx2 = min(tw, bx + bw + pad)
                surrounding = gray_torso[sy1:sy2, sx1:sx2]
                contrast = abs(float(np.mean(card_roi)) - float(np.mean(surrounding)))
                if contrast < 10.0:
                    continue
                    
                score = 0.65
                score += min(0.18, (mean_grad / 40.0) * 0.18)
                score += min(0.12, (contrast / 40.0) * 0.12)
                score += 0.05 if rect_fill > 0.72 else 0.0
                
                if score > best_card_score:
                    best_card_score = score
                    best_card = {
                        "box": (tx + bx, ty + by, bw, bh),
                        "rel_box": (bx, by, bw, bh),
                        "score": score
                    }

            # 5. Corroboration & Verification Logic
            lanyard_details = None
            if best_lanyard:
                lx1, ly1 = best_lanyard["left"]["pt1"]
                lx2, ly2 = best_lanyard["left"]["pt2"]
                rx1, ry1 = best_lanyard["right"]["pt1"]
                rx2, ry2 = best_lanyard["right"]["pt2"]
                lanyard_details = {
                    "left": [int(tx + lx1), int(ty + ly1), int(tx + lx2), int(ty + ly2)],
                    "right": [int(tx + rx1), int(ty + ry1), int(tx + rx2), int(ty + ry2)],
                    "meet": [int(tx + best_lanyard["meet"][0]), int(ty + best_lanyard["meet"][1])]
                }

            # Case A: Both Lanyard AND ID Card Badge detected
            if best_lanyard and best_card:
                mx, my = best_lanyard["meet"]
                cbx, cby, cbw, cbh = best_card["rel_box"]
                dist_to_meet = np.hypot(cbx + cbw / 2.0 - mx, cby - my)
                if dist_to_meet <= max(45, 0.55 * fw):
                    final_conf = min(0.98, best_card_score + 0.18)
                    return {
                        "detected": True,
                        "box": best_card["box"],
                        "confidence": round(final_conf, 2),
                        "status": "Detected (Compliant)",
                        "details": {
                            "has_lanyard": True,
                            "has_badge": True,
                            "lanyard_lines": lanyard_details
                        }
                    }

            # Case B: Lanyard straps detected — verify badge at meeting point
            if best_lanyard:
                mx, my = best_lanyard["meet"]
                est_bw = int(fw * 0.42)
                est_bh = int(est_bw * 1.45)
                est_bx = max(0, int(mx - est_bw / 2.0))
                est_by = max(0, my)

                badge_confirmed = False
                if est_bx + est_bw <= tw and est_by + est_bh <= th:
                    candidate_patch = gray_torso[est_by:est_by + est_bh, est_bx:est_bx + est_bw]
                    if candidate_patch.size > 0:
                        p_var = float(np.var(candidate_patch))
                        p_sob = cv2.Sobel(candidate_patch, cv2.CV_32F, 1, 0, ksize=3)
                        p_grad = float(np.mean(np.abs(p_sob)))
                        # Require strong texture evidence (text/photo on badge)
                        if p_var > 600 and p_grad > 25.0:
                            badge_confirmed = True

                if badge_confirmed:
                    final_conf = round(min(0.92, best_lanyard["score"] + 0.10), 2)
                    return {
                        "detected": True,
                        "box": (tx + est_bx, ty + est_by, est_bw, est_bh),
                        "confidence": final_conf,
                        "status": "Detected (Compliant)",
                        "details": {
                            "has_lanyard": True,
                            "has_badge": True,
                            "lanyard_lines": lanyard_details
                        }
                    }
                else:
                    # Lanyard straps found but no ID badge — still a violation
                    return {
                        "detected": False,
                        "box": None,
                        "confidence": 0.0,
                        "status": "Missing / Not Visible (Violation)",
                        "details": {
                            "has_lanyard": True,
                            "has_badge": False,
                            "lanyard_lines": lanyard_details
                        }
                    }



            # Case C: ID Card Badge clearly detected (clipped badge on chest without lanyard)
            if best_card and best_card_score >= 0.72:
                return {
                    "detected": True,
                    "box": best_card["box"],
                    "confidence": round(best_card_score, 2),
                    "status": "Detected (Compliant)",
                    "details": {
                        "has_lanyard": False,
                        "has_badge": True,
                        "lanyard_lines": None
                    }
                }

            # Case D: No ID Card or Lanyard found (Missing / Violation)
            return {
                "detected": False,
                "box": None,
                "confidence": 0.0,
                "status": "Missing / Not Visible (Violation)",
                "details": {
                    "has_lanyard": False,
                    "has_badge": False,
                    "lanyard_lines": None
                }
            }
        except Exception as e:
            print(f"[AIEngine] ID card detect error: {e}")
            return {
                "detected": False,
                "box": None,
                "confidence": 0.0,
                "status": "Missing / Not Visible (Violation)",
                "details": {"has_lanyard": False, "has_badge": False}
            }

    # ----------------- HAIRCUT / HAIR LENGTH ANALYZER -----------------
    def analyze_haircut(self, image_bgr, face_box):
       
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
        Detects whether the person is wearing shoes using MediaPipe pose
        landmarks (ankles, heels, foot tips) and colour/texture analysis
        of the foot region.

        Returns dict with: detected (bool|None), status (str), box, confidence.
        """
        h_img, w_img = image_bgr.shape[:2]

        # 1. Obtain pose landmarks if not provided
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
            try:
                l_ankle = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
                r_ankle = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
                l_heel  = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_HEEL.value]
                r_heel  = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_HEEL.value]
                l_foot  = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value]
                r_foot  = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value]

                # Visibility: accept if any ankle/heel has visibility > 0.10
                max_ankle_vis = max(l_ankle.visibility, r_ankle.visibility,
                                    l_heel.visibility, r_heel.visibility)

                # Feet "in frame": at least one foot-tip y < 1.10 (allows slightly
                # clipped feet) AND ankle y > 0.35 (not wildly above the frame)
                min_foot_y = min(l_foot.y, r_foot.y)
                max_ankle_y = max(l_ankle.y, r_ankle.y)

                if max_ankle_vis > 0.10 and min_foot_y < 1.10 and max_ankle_y > 0.35:
                    # Build bounding box from all lower-limb landmarks
                    xs = [l_ankle.x, r_ankle.x, l_heel.x, r_heel.x, l_foot.x, r_foot.x]
                    ys_top = [l_ankle.y, r_ankle.y]
                    ys_bot = [l_heel.y, r_heel.y, l_foot.y, r_foot.y]

                    fx1 = int(min(xs) * w_img) - 25
                    fy1 = int(min(ys_top) * h_img) - 15
                    fx2 = int(max(xs) * w_img) + 25
                    fy2 = int(max(ys_bot) * h_img) + 25

                    fx1 = max(0, fx1)
                    fy1 = max(0, fy1)
                    fx2 = min(w_img, fx2)
                    fy2 = min(h_img, fy2)

                    if fy2 > fy1 + 5 and fx2 > fx1 + 5:
                        shoe_roi = image_bgr[fy1:fy2, fx1:fx2]
                        if shoe_roi.size > 0:
                            # --- Colour analysis ---
                            hsv_feet = cv2.cvtColor(shoe_roi, cv2.COLOR_BGR2HSV)
                            skin_mask = cv2.inRange(hsv_feet,
                                                    np.array([0, 20, 70]),
                                                    np.array([20, 255, 255]))
                            skin_ratio = np.sum(skin_mask > 0) / float(shoe_roi.size // 3)

                            # Dark pixel ratio (shoes are usually dark)
                            gray_shoe = cv2.cvtColor(shoe_roi, cv2.COLOR_BGR2GRAY)
                            dark_ratio = np.sum(gray_shoe < 80) / float(gray_shoe.size)

                            # Edge density (shoe outline / texture)
                            edge_density = np.sum(
                                cv2.Canny(gray_shoe, 50, 150) > 0
                            ) / float(gray_shoe.size)

                            # Decision: shoes are dark, non-skin, with some structure
                            shoe_score = 0.0
                            if skin_ratio < 0.30:
                                shoe_score += 0.40
                            elif skin_ratio < 0.45:
                                shoe_score += 0.15

                            if dark_ratio > 0.50:
                                shoe_score += 0.35
                            elif dark_ratio > 0.30:
                                shoe_score += 0.15

                            if edge_density > 0.02:
                                shoe_score += 0.15

                            # Confidence scales with ankle visibility
                            vis_factor = min(1.0, max_ankle_vis / 0.60)
                            confidence = round(0.55 + shoe_score * vis_factor * 0.40, 2)

                            box = (fx1, fy1, fx2 - fx1, fy2 - fy1)

                            if shoe_score >= 0.55:
                                return {
                                    "detected": True,
                                    "status": "Shoes Worn (Compliant)",
                                    "box": box,
                                    "confidence": min(0.96, confidence)
                                }
                            else:
                                return {
                                    "detected": False,
                                    "status": "Barefoot / Slippers (Violation)",
                                    "box": box,
                                    "confidence": min(0.90, confidence)
                                }
            except Exception as e:
                print(f"[AIEngine] Pose feet parsing error: {e}")

        # 2. Fallback: no reliable pose landmarks for feet.
        # Only report "out of frame" - do NOT guess from edge density alone
        # as it produces too many false positives on cluttered floors.
        return {
            "detected": None,
            "status": "Upper Body (Out of Frame)",
            "box": None,
            "confidence": 0.50
        }


    # ----------------- FULL FRAME MULTI-MODAL INSPECTION -----------------
    def inspect_full_frame(self, image_bgr, enrolled_students=None):
        
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
                    "status": id_card["status"],
                    "details": id_card.get("details", {})
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
            id_color = (95, 227, 214) if id_ok else (70, 70, 240) # Cyan/Green or Red
            id_text = "ID: OK" if id_ok else "ID: MISSING"
            
            # If lanyard lines were detected, render them on the HUD
            lanyard_lines = id_card.get('details', {}).get('lanyard_lines')
            if lanyard_lines:
                ll = lanyard_lines.get('left')
                rl = lanyard_lines.get('right')
                if ll and len(ll) == 4:
                    cv2.line(frame, (ll[0], ll[1]), (ll[2], ll[3]), (95, 227, 214), 2)
                if rl and len(rl) == 4:
                    cv2.line(frame, (rl[0], rl[1]), (rl[2], rl[3]), (95, 227, 214), 2)
            
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
