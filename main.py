"""
ParkVision — Main Entry Point
==============================
Launches the full parking-analysis pipeline on a video file or RTSP stream.

Usage
-----
    python main.py <video_path_or_rtsp_url> [--model yolov8s.pt] [--skip 3]

Arguments
---------
  source          Path to a video file (MP4, AVI, etc.) or an RTSP URL.
  --model         YOLOv8 model weights file. Default: yolov8s.pt.
  --skip          Run full inference every N frames. Default: 3.
  --slots         Path to bounding_boxes.json. Default: ./bounding_boxes.json.
  --db            Path to SQLite database file. Default: ./parkvision.db.

Author : ParkVision
"""

import argparse
import logging
import sys
from pathlib import Path

from core.config import Config
from core.video_processor import VideoProcessor


def _configure_logging() -> None:
    """Set up clean, readable console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ParkVision",
        description="Aerial parking management system with YOLO + ByteTrack.",
    )
    parser.add_argument(
        "source",
        help="Video file path or RTSP stream URL (e.g. rtsp://192.168.1.10/stream)",
    )
    parser.add_argument(
        "--model",
        default="yolov8s.pt",
        help="YOLOv8 weights file (default: yolov8s.pt)",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=3,
        metavar="N",
        help="Run full inference every N frames (default: 3)",
    )
    parser.add_argument(
        "--slots",
        default=None,
        help="Path to bounding_boxes.json (default: ./bounding_boxes.json)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite database path (default: ./parkvision.db)",
    )
    return parser.parse_args()


def main() -> None:
    _configure_logging()
    logger = logging.getLogger(__name__)

    args = _parse_args()

    # ── Validate source ───────────────────────────────────────────────────────
    source = args.source
    is_rtsp = source.startswith("rtsp://") or source.startswith("rtmp://")
    if not is_rtsp and not Path(source).exists():
        logger.error("Source file not found: %s", source)
        sys.exit(1)

    # ── Build config ──────────────────────────────────────────────────────────
    cfg = Config(yolo_model=args.model,
                 inference_every_n_frames=args.skip)

    if args.slots:
        cfg.slots_json = Path(args.slots)
    if args.db:
        cfg.db_path = Path(args.db)

    logger.info("=" * 60)
    logger.info("  ParkVision  —  Aerial Parking Management System")
    logger.info("=" * 60)
    logger.info("  Source  : %s", source)
    logger.info("  Model   : %s", cfg.yolo_model)
    logger.info("  Slots   : %s", cfg.slots_json)
    logger.info("  DB      : %s", cfg.db_path)
    logger.info("  Proc res: %dx%d", cfg.proc_width, cfg.proc_height)
    logger.info("  Inf skip: every %d frame(s)", cfg.inference_every_n_frames)
    logger.info("=" * 60)

    # ── Run pipeline ─────────────────────────────────────────────────────────
    processor = VideoProcessor(source=source, config=cfg)
    processor.run()

    logger.info("\n✓  Output saved → %s", cfg.output_final)
    logger.info("✓  Database     → %s", cfg.db_path)
    logger.info("\nTo launch the dashboard run:")
    logger.info("  streamlit run dashboard.py -- --db %s\n", cfg.db_path)


if __name__ == "__main__":
    main()
