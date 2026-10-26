"""
===============================================================================
  Campus-Eye: System Architecture Diagram Generator (IEEE Publication Quality)
  Generates a multi-layered architecture diagram suitable for IEEE papers.
  Output: system_architecture.png / .pdf (300 DPI)
===============================================================================
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

# --- IEEE-friendly figure settings ---
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['DejaVu Serif', 'Georgia', 'Times New Roman'],
    'font.size': 9,
    'axes.linewidth': 0.8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
})

fig, ax = plt.subplots(1, 1, figsize=(7.16, 10.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 15.5)
ax.axis('off')

# --- Color Palette ---
C = {
    'L1': '#DCEEFB', 'L2': '#FFF3E0', 'L3': '#E0F2E9',
    'L4': '#EDE0F5', 'L5': '#FDEBED',
    'mod': '#FFFFFF', 'bdr': '#37474F', 'arr': '#455A64',
    'hdr': '#1A237E', 'txt': '#455A64', 'acc': '#1565C0',
}

def layer(ax, x, y, w, h, color, label):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.14",
                       fc=color, ec=C['bdr'], lw=1.4, zorder=1)
    ax.add_patch(p)
    ax.text(x + w/2, y + h - 0.25, label, fontsize=10, fontweight='bold',
            ha='center', va='top', color=C['hdr'], fontstyle='italic', zorder=5)

def mod(ax, x, y, w, h, title, sub="", hl=False):
    ec = C['acc'] if hl else C['bdr']
    lw = 1.4 if hl else 0.9
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                       fc=C['mod'], ec=ec, lw=lw, zorder=3)
    ax.add_patch(p)
    if sub:
        ax.text(x + w/2, y + h/2 + 0.17, title, fontsize=7.2,
                fontweight='bold', ha='center', va='center', color=C['hdr'], zorder=5)
        ax.text(x + w/2, y + 0.17, sub, fontsize=5.5, ha='center',
                va='bottom', color=C['txt'], style='italic', zorder=5)
    else:
        ax.text(x + w/2, y + h/2, title, fontsize=7.2, fontweight='bold',
                ha='center', va='center', color=C['hdr'], zorder=5)

def arrow(ax, x1, y1, x2, y2, label="", bidi=False, color=None):
    c = color or C['arr']
    s = '<->' if bidi else '->'
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=s,
                        mutation_scale=13, lw=1.2, color=c, zorder=2)
    ax.add_patch(a)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.08, my, label, fontsize=5.8, color=c, ha='left',
                va='center', fontstyle='italic', zorder=5,
                bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.9))

# =========================================================================
#  TITLE
# =========================================================================
ax.text(5, 15.2, 'Campus-Eye: System Architecture',
        fontsize=14, fontweight='bold', ha='center', va='top', color=C['hdr'])
ax.text(5, 14.75,
        'Multi-Modal Edge AI Surveillance & Automated Compliance Monitoring Suite',
        fontsize=8, ha='center', va='top', color=C['txt'], fontstyle='italic')

# =========================================================================
#  LAYER 1: DATA ACQUISITION (Y: 12.6 - 14.4)
# =========================================================================
Y1 = 12.6
layer(ax, 0.3, Y1, 9.4, 1.85, C['L1'],
      'Layer 1: Data Acquisition & Ingestion')

mod(ax, 0.65, Y1+0.22, 2.0, 1.1, 'USB Webcam', 'OpenCV + DSHOW\n640x480 BGR')
mod(ax, 3.05, Y1+0.22, 2.0, 1.1, 'IP / RTSP Stream', 'Network Cameras\nVariable Resolution')
mod(ax, 5.45, Y1+0.22, 2.0, 1.1, 'Simulated Feeds', 'Synthetic Frames\n640x420 NumPy')
mod(ax, 7.85, Y1+0.22, 1.55, 1.1, 'Frame Queue', 'Multi-threaded\n~25 FPS')

# =========================================================================
#  LAYER 2: AI ENGINE (Y: 9.0 - 12.2)
# =========================================================================
Y2 = 9.0
layer(ax, 0.3, Y2, 9.4, 3.2, C['L2'],
      'Layer 2: Multi-Modal AI Detection & Analysis Engine')

# Row A: Face pipeline
mod(ax, 0.55, Y2+1.75, 1.72, 1.0, 'Face Detection', 'Haar Cascade\nOpenCV', hl=True)
mod(ax, 2.47, Y2+1.75, 1.72, 1.0, 'Feature Extraction', '160-D Histogram\nHSV+Sobel+Grid', hl=True)
mod(ax, 4.39, Y2+1.75, 1.72, 1.0, 'Face Matching', 'Cosine Similarity\nThreshold = 0.65', hl=True)
mod(ax, 6.31, Y2+1.75, 1.5, 1.0, 'MediaPipe Pose', 'Skeletal Landmark\n33 Keypoints')
mod(ax, 8.01, Y2+1.75, 1.5, 1.0, 'HUD Renderer', 'Cyberpunk Overlay\nReal-time')

# Row B: Compliance modules
mod(ax, 0.55, Y2+0.3, 2.05, 1.1, 'ID Card Detection', 'Canny + Contour\nHough Transform')
mod(ax, 2.85, Y2+0.3, 2.05, 1.1, 'Haircut Analysis', 'Dark Pixel Segm.\nRatio Thresholds')
mod(ax, 5.15, Y2+0.3, 2.05, 1.1, 'Shoe Detection', 'Pose Keypoints\nHSV Skin Ratio')
mod(ax, 7.45, Y2+0.3, 2.05, 1.1, 'Crowd Estimation', 'Face Count vs.\nCapacity Limit')

# Pipeline arrows inside L2
arrow(ax, 2.27, Y2+2.25, 2.47, Y2+2.25, '')
arrow(ax, 4.19, Y2+2.25, 4.39, Y2+2.25, '')

# =========================================================================
#  LAYER 3: BACKEND SERVER (Y: 6.0 - 8.6)
# =========================================================================
Y3 = 6.0
layer(ax, 0.3, Y3, 9.4, 2.6, C['L3'],
      'Layer 3: Flask REST API Backend Server (Python)')

mod(ax, 0.55, Y3+0.3, 1.55, 1.75, 'MJPEG Stream\nServer', '/video_feed\n/video_frame')
mod(ax, 2.3, Y3+0.3, 1.65, 1.75, 'AI Inspection\nAPI', '/api/inspect_frame\nMulti-Modal Audit')
mod(ax, 4.15, Y3+0.3, 1.55, 1.75, 'Student & Face\nEnrollment', '/api/students\n/api/enroll')
mod(ax, 5.9, Y3+0.3, 1.65, 1.75, 'Attendance &\nAlerts API', '/api/attendance\n/api/alerts')
mod(ax, 7.75, Y3+0.3, 1.75, 1.75, 'Camera CRUD\n& Stats API', '/api/cameras\n/api/stats')

# =========================================================================
#  LAYER 4: DATABASE (Y: 3.2 - 5.5)
# =========================================================================
Y4 = 3.4
layer(ax, 0.3, Y4, 9.4, 2.2, C['L4'],
      'Layer 4: Persistent Storage (SQLite + File System)')

mod(ax, 0.6, Y4+0.25, 2.0, 1.35, 'students', 'Enrollment Records\n160-D Embeddings (JSON)')
mod(ax, 2.85, Y4+0.25, 2.0, 1.35, 'cameras', 'Source Config, Mode\nCapacity Limits')
mod(ax, 5.1, Y4+0.25, 2.0, 1.35, 'attendance', 'Compliance Ledger\nMulti-Modal Status')
mod(ax, 7.35, Y4+0.25, 2.15, 1.35, 'alerts', 'Violation Records\nEvidence Snapshots')

# =========================================================================
#  LAYER 5: FLUTTER FRONTEND (Y: 0.7 - 3.0)
# =========================================================================
Y5 = 0.8
layer(ax, 0.3, Y5, 9.4, 2.2, C['L5'],
      'Layer 5: Flutter Cross-Platform Dashboard (Web / Mobile / Desktop)')

mod(ax, 0.55, Y5+0.2, 1.55, 1.4, 'Dashboard', 'KPI Cards, Stats\nCompliance Rates')
mod(ax, 2.3, Y5+0.2, 1.55, 1.4, 'Live Surveillance', 'MJPEG Viewer\nReal-time HUD')
mod(ax, 4.05, Y5+0.2, 1.55, 1.4, 'Enrollment UI', 'Camera Capture\nPhoto Upload')
mod(ax, 5.8, Y5+0.2, 1.55, 1.4, 'Students', 'Roster Mgmt.\nSearch & Filter')
mod(ax, 7.55, Y5+0.2, 1.95, 1.4, 'Attendance &\nAlerts', 'CSV Export\nResolution Track.')

# =========================================================================
#  INTER-LAYER ARROWS (properly spaced)
# =========================================================================

# L1 -> L2 (center)
arrow(ax, 5, Y1, 5, Y2+3.2, 'BGR Frames', color='#1565C0')

# L2 -> L3 (center)
arrow(ax, 5, Y2, 5, Y3+2.6, 'Detection JSON', color='#2E7D32')

# L3 <-> L4 (two columns)
arrow(ax, 2.8, Y3, 2.8, Y4+2.2, 'SQL R/W', bidi=True, color='#6A1B9A')
arrow(ax, 7.2, Y3, 7.2, Y4+2.2, 'JPEG I/O', bidi=True, color='#6A1B9A')

# L4 <-> L5 is WRONG -- L3 talks to L5, not L4
# L3 <-> L5 (REST API / HTTP)
arrow(ax, 3.8, Y4, 3.8, Y5+2.2, '', bidi=False, color='#9E9E9E')
arrow(ax, 6.2, Y4, 6.2, Y5+2.2, '', bidi=False, color='#9E9E9E')

# Add labels for L3<->L5 connection on the sides
ax.text(0.08, (Y3 + Y5+2.2)/2, 'REST API\n(HTTP/JSON)', fontsize=6,
        ha='center', va='center', color='#C62828', rotation=90,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.2', fc='#FFEBEE', ec='#C62828', lw=0.6))

ax.text(9.92, (Y3 + Y5+2.2)/2, 'MJPEG\nStreaming', fontsize=6,
        ha='center', va='center', color='#1565C0', rotation=90,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.2', fc='#E3F2FD', ec='#1565C0', lw=0.6))

# Side bracket lines L3 <-> L5
ax.annotate('', xy=(0.22, Y5+2.2), xytext=(0.22, Y3),
            arrowprops=dict(arrowstyle='<->', color='#C62828', lw=1.5))
ax.annotate('', xy=(9.78, Y5+2.2), xytext=(9.78, Y3),
            arrowprops=dict(arrowstyle='<->', color='#1565C0', lw=1.5))

# =========================================================================
#  FIGURE CAPTION
# =========================================================================
ax.text(5, 0.32,
        'Fig. 1.  System architecture of the Campus-Eye multi-modal edge AI '
        'surveillance framework showing the five-layer\n'
        'pipeline from data acquisition through AI inference, REST API, '
        'persistent storage, and cross-platform Flutter dashboard.',
        fontsize=7, ha='center', va='bottom', color=C['txt'],
        fontstyle='italic',
        bbox=dict(boxstyle='round,pad=0.25', fc='#FAFAFA', ec='#BDBDBD', lw=0.5))

# --- Save ---
output_dir = os.path.dirname(os.path.abspath(__file__))
png_path = os.path.join(output_dir, 'system_architecture.png')
pdf_path = os.path.join(output_dir, 'system_architecture.pdf')

plt.savefig(png_path, dpi=300, facecolor='white', edgecolor='none')
try:
    plt.savefig(pdf_path, dpi=300, facecolor='white', edgecolor='none', format='pdf')
except Exception:
    pass
plt.close()

print("")
print("=" * 65)
print("  System Architecture Diagram Generated Successfully!")
print(f"  PNG: {png_path}")
print(f"  PDF: {pdf_path}")
print("  Resolution: 300 DPI | Size: 7.16 x 10.5 in (IEEE)")
print("=" * 65)
print("")
