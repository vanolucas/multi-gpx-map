"""Draft: GPX points on map."""

import logging
import re
from pathlib import Path

import folium
import gpxpy
from defusedxml.ElementTree import ParseError, fromstring
from fitparse import FitFile

logging.basicConfig(level=logging.INFO)


def load_points_from_gpx(gpx_file_path: Path) -> list[tuple[float, float]]:
    """
    Parse a GPX file and extract the coordinates.

    :param gpx_file: Path to the GPX file.
    :return: A list of tuples where each tuple is a pair of (latitude, longitude).
    """
    with gpx_file_path.open() as f:
        gpx = gpxpy.parse(f)

    points: list[tuple[float, float]] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))  # noqa: PERF401

    return points


def load_points_from_fit(fit_file_path: Path) -> list[tuple[float, float]]:
    """
    Parse a FIT file and extract the coordinates.

    :param fit_file: Path to the FIT file.
    :return: A list of tuples where each tuple is a pair of (latitude, longitude).
    """
    points: list[tuple[float, float]] = []

    fit = FitFile(fit_file_path.as_posix())
    # Iterate over all records of type 'record' (which contain the GPS data).
    for record in fit.get_messages("record"):
        # Each 'record' message can contain multiple pieces of data
        # (like timestamp, position_lat, position_long, etc.).

        # Initialize variables to hold latitude and longitude.
        latitude = None
        longitude = None

        for data in record:
            # Check for latitude and longitude data.
            if data.name == "position_lat":
                # Convert semicircles to degrees.
                latitude = data.value * (180.0 / 2**31)
            elif data.name == "position_long":
                # Convert semicircles to degrees.
                longitude = data.value * (180.0 / 2**31)

        # If both latitude and longitude were found, add them as a tuple to the list.
        if latitude is not None and longitude is not None:
            points.append((latitude, longitude))

    return points


def load_points_from_tcx(tcx_file_path: Path) -> list[tuple[float, float]]:
    """
    Parse a TCX file and extract the coordinates.

    :param fit_file: Path to the TCX file.
    :return: A list of tuples where each tuple is a pair of (latitude, longitude).
    """
    # Define namespaces to handle the TCX schema.
    namespaces = {"ns": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}

    points: list[tuple[float, float]] = []

    try:
        # Open and read the file, then strip leading whitespace/BOM.
        with tcx_file_path.open(encoding="utf-8-sig") as file:
            content = file.read()
            cleaned_content = re.sub(r"^\s+", "", content, flags=re.UNICODE)

        # Parse the cleaned XML content.
        root = fromstring(cleaned_content)

        # Iterate through each Trackpoint element in the TCX file.
        for trackpoint in root.findall(".//ns:Trackpoint", namespaces):
            # Try to find the Position, then LatitudeDegrees and LongitudeDegrees elements.
            position = trackpoint.find("ns:Position", namespaces)
            if position is not None:
                latitude = position.find("ns:LatitudeDegrees", namespaces)
                longitude = position.find("ns:LongitudeDegrees", namespaces)
                if latitude is not None and longitude is not None:
                    # Add the latitude and longitude to the list as a tuple.
                    points.append((float(latitude.text), float(longitude.text)))

    except ParseError as e:
        logging.exception("Error parsing the TCX file: %s", exc_info=e)
        return []
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


def add_track_to_map(
    points: list[tuple[float, float]],
    folium_map: folium.Map,
    max_points: int = 100,
    color: str = "blue",
) -> None:
    """Add the provided track to the provided map (if it is long enough)."""
    min_track_points = 4
    if len(points) < min_track_points:
        return
    # Resample track.
    track = resample_track(points, max_points)
    # Add track to map.
    folium.PolyLine(track, color=color, weight=2.5, opacity=1).add_to(folium_map)


def add_track_file_to_map(
    file_path: Path,
    folium_map: folium.Map,
    max_points: int = 100,
    color: str = "blue",
) -> None:
    """Load track from the specified file and add it to the provided map."""
    extension = file_path.suffix[1:].upper()
    logging.info("Processing %s file: %s", extension, file_path.as_posix())
    # Load track.
    loaders = {
        "GPX": load_points_from_gpx,
        "FIT": load_points_from_fit,
        "TCX": load_points_from_tcx,
    }
    loader = loaders[extension]
    points = loader(file_path)
    # Add it to the map.
    add_track_to_map(points, folium_map, max_points, color)


def add_track_files_to_map(
    dir_path: Path,
    file_format: str,
    folium_map: folium.Map,
    max_points: int = 100,
    color: str = "blue",
) -> None:
    """Add all activity track files of the specified format to the provided map."""
    files = dir_path.glob(f"*.{file_format.lower()}")
    for file in files:
        add_track_file_to_map(file, folium_map, max_points, color)


if __name__ == "__main__":
    RESAMPLE_MAX_POINTS_PER_TRACK = 100
    DIR_PATH = Path("data/activities/")

    # Create map.
    folium_map = folium.Map(location=[0, 0], zoom_start=2)

    # Process all activity files.
    file_formats = ["gpx", "fit", "tcx"]
    color = {"gpx": "blue", "fit": "red", "tcx": "green"}
    for file_format in file_formats:
        add_track_files_to_map(
            DIR_PATH,
            file_format,
            folium_map,
            max_points=RESAMPLE_MAX_POINTS_PER_TRACK,
            color=color[file_format],
        )

    # Save map.
    folium_map.save("map.html")
