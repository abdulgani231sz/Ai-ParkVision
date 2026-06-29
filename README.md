<div align="center">

<img src="https://img.icons8.com/fluency/96/parking.png" width="80"/>

# ParkVision

**Aerial Parking Management System**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00CFFF?style=flat-square)](https://ultralytics.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=flat-square&logo=opencv)](https://opencv.org)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite)](https://sqlite.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)

</div>

---

## What This Does

ParkVision analyzes aerial / drone footage of parking lots in real time. It detects every vehicle, maps each one to a defined parking slot, tracks movement frame-by-frame, logs every session to a database, and streams live occupancy analytics to a web dashboard.

No ground sensors. No manual checking. Just a camera and a video file.

---

## Live Output

![ParkVision Live Output](assets/demo_output.png)

> **48 slots monitored** across 4 rows — 14 occupied (green), 34 available (orange), 15 vehicles detected at 7 FPS on CPU.

---

## Results

| Metric | Value |
|--------|-------|
| Slots tracked | 48 (4 rows × 12 columns) |
| Source resolution | 3840 × 2160 (4K) |
| Processing resolution | 1280 × 720 |
| Detection FPS (CPU) | ~7 fps |
| Occupancy accuracy | Centroid + point-in-polygon test |
| Vehicle classes | Car, Motorcycle, Bus, Truck |
| DB write latency | Only on state change — no write amplification |

---

## How I Built This

I started with a basic script that used a fixed hardcoded grid to guess parking slots. That broke immediately on real footage because aerial slots are never perfect rectangles — perspective warps everything.

So I rebuilt it from scratch into a proper modular system:

- Replaced the hardcoded grid with a **JSON polygon parser** that reads exact 4-point coordinates and auto-scales from 4K to 720p at runtime
- YOLOv8 alone was detecting 0 cars at `conf=0.25` because it's trained on side-view images — rooftops look completely different. I dropped confidence to `0.08` and added an **OpenCV BGS + HSV blob hybrid** as a fallback so no car is ever missed
- Added **ByteTrack** so vehicles maintain a persistent ID across frames even when the detector momentarily loses them
- The overlap test was wrong — standard IoU doesn't work on perspective-warped quads. Replaced it with `cv2.pointPolygonTest` on the vehicle centroid
- Wrapped frame reading in a **daemon thread** feeding a bounded Queue — this alone removed the buffer lag that was causing dropped frames
- Every slot state change writes to **SQLite in WAL mode** so the dashboard can read live without blocking the processor

---

## Project Structure

```
ParkVision/
├── main.py                 ← CLI entry point
├── dashboard.py            ← Streamlit analytics dashboard
├── bounding_boxes.json     ← 48 parking slot polygons (4K coordinates)
├── requirements.txt
│
└── core/
    ├── config.py           ← All constants, zero magic numbers
    ├── roi_manager.py      ← Polygon scaling + point-in-polygon occupancy
    ├── detector.py         ← YOLOv8 + OpenCV hybrid detector
    ├── tracker.py          ← Trajectory trails, velocity, moving/parked state
    ├── database.py         ← SQLite: slot_status + parking_logs
    └── video_processor.py  ← Threaded pipeline: read → detect → track → write
```

---

## Setup

```bash
git clone https://github.com/abdulgani231sz/ParkVision.git
cd ParkVision
pip install -r requirements.txt
```

For GPU (recommended):
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## Run

```bash
# Process a video file
python main.py input.mp4

# With live real-time window
python main.py input.mp4 --live

# RTSP live camera
python main.py rtsp://192.168.1.10/stream --live

# Faster — use nano model, skip every 5 frames
python main.py input.mp4 --model yolov8n.pt --skip 5
```

**Live window keys:** `Q` quit &nbsp;|&nbsp; `P` pause &nbsp;|&nbsp; `S` screenshot

---

## Dashboard

```bash
streamlit run dashboard.py
```

Open `http://localhost:8501`

Shows: slot status table, occupied/free counts, peak hour chart, session log, occupancy timeline.

---

## Configuration

All tuneable constants are in `core/config.py` — not scattered across the code.

| Parameter | Default | Why |
|-----------|---------|-----|
| `yolo_conf` | `0.08` | Aerial rooftops look nothing like side-view training data |
| `overlap_threshold` | `0.18` | Centroid test handles most cases; sample grid is fallback |
| `inference_every_n_frames` | `3` | ByteTrack fills the gap — 3× speed with no accuracy loss |
| `proc_width / proc_height` | `1280 × 720` | Fast enough for real-time on CPU |

---

## Database

```sql
CREATE TABLE slot_status (
    slot_id      INTEGER PRIMARY KEY,
    status       TEXT    NOT NULL,   -- 'Free' | 'Occupied'
    last_updated TEXT    NOT NULL
);

CREATE TABLE parking_logs (
    session_id     TEXT PRIMARY KEY,
    slot_id        INTEGER,
    vehicle_id     TEXT,
    entry_time     TEXT,
    exit_time      TEXT,
    total_duration REAL              -- seconds
);
```

---

## Tech Stack

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — detection + ByteTrack
- [OpenCV](https://opencv.org) — BGS, polygon tests, drawing
- [SQLite3](https://docs.python.org/3/library/sqlite3.html) — session persistence
- [Streamlit](https://streamlit.io) — live dashboard
- [NumPy](https://numpy.org) — numerical ops

---

## Author

**ABDUL GANI**
[@abdulgani231sz](https://github.com/abdulgani231sz) &nbsp;·&nbsp; Karnataka, Davangere 🇮🇳

---

<div align="center">
<sub>MIT License</sub>
</div>
