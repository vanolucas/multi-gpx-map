"""Draft: GPX points on map."""

import logging
from pathlib import Path

import folium
import gpxpy

logging.basicConfig(level=logging.INFO)


def load_points_from_gpx(gpx_file: Path) -> list[tuple[float, float]]:
    """
    Parse a GPX file and extract the coordinates.

    :param gpx_file_path: Path to the GPX file.
    :return: A list of tuples where each tuple is a pair of (latitude, longitude).
    """
    with gpx_file.open() as f:
        gpx = gpxpy.parse(f)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))  # noqa: PERF401

    return points


def resample_track(
    points: list[tuple[float, float]], max_points: int = 100
) -> list[tuple[float, float]]:
    """Resample the track to have a maximum of max_points points."""
    # Calculate interval to achieve the desired number of points
    interval = len(points) / max_points
    resampled = []

    # Select points at regular intervals
    for i in range(max_points):
        idx = int(i * interval)
        if idx < len(points):
            resampled.append(points[idx])

    return resampled


if __name__ == "__main__":
    MIN_TRACK_POINTS = 4

    # Get paths of GPX files.
    gpx_files = Path("data/activities/").glob("*.gpx")

    # Create map.
    folium_map = folium.Map(location=[0, 0], zoom_start=2)

    # Process each GPX file.
    for gpx_file in gpx_files:
        logging.info("Processing GPX file: %s", gpx_file.as_posix())
        # Load track.
        points = load_points_from_gpx(gpx_file)
        if len(points) < MIN_TRACK_POINTS:
            continue
        # Resample track.
        track = resample_track(points, max_points=100)
        # Add track to map.
        folium.PolyLine(track, color="blue", weight=2.5, opacity=1).add_to(folium_map)

    # Save map.
    folium_map.save("map.html")
