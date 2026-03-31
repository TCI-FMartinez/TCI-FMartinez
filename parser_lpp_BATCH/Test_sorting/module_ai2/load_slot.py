#!/usr/bin/env python3
"""
Python translation of loadSlot.m and all its dependencies.
Complete standalone implementation for processing TCI G-Code files.
"""

import json
import math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from scipy.spatial import Delaunay
from scipy.spatial.distance import cdist
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely import affinity
from collections import defaultdict


# Global constants
CW = -1
CCW = 1
INNER_CONT = 1
OUTER_CONT = 0


def polygon_to_geojson(polygon: Polygon) -> Dict[str, Any]:
    """
    Convert Shapely Polygon to GeoJSON format.
    
    Args:
        polygon: Shapely Polygon object
        
    Returns:
        Dictionary in GeoJSON Polygon format
    """
    if polygon is None or not isinstance(polygon, Polygon):
        return None
    
    try:
        # Extract exterior coordinates
        exterior_coords = list(polygon.exterior.coords)
        
        # Extract interior coordinates (holes)
        holes = []
        for interior in polygon.interiors:
            holes.append(list(interior.coords))
        
        # Build coordinates array: [exterior, hole1, hole2, ...]
        coordinates = [exterior_coords]
        if holes:
            coordinates.extend(holes)
        
        # Create GeoJSON Polygon
        geojson_polygon = {
            "type": "Polygon",
            "coordinates": coordinates
        }
        
        return geojson_polygon
        
    except Exception as e:
        print(f"Error converting polygon to GeoJSON: {e}")
        return None


def serialize_for_json(obj):
    """
    Convert numpy and other non-serializable objects to JSON-compatible types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable object
    """
    if isinstance(obj, Polygon):
        # Convert Shapely Polygon to GeoJSON
        return polygon_to_geojson(obj)
    elif isinstance(obj, Point):
        # Convert Point to GeoJSON Point
        return {
            "type": "Point",
            "coordinates": [obj.x, obj.y]
        }
    elif isinstance(obj, np.ndarray):
        # Convert numpy arrays to lists
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        # Convert numpy scalar types
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, dict):
        # Recursively process dictionaries
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # Recursively process lists and tuples
        return [serialize_for_json(item) for item in obj]
    else:
        # Return as-is for JSON-serializable types
        return obj


@dataclass
class CuttingUnit:
    """Structure for cutting unit information"""
    machine: str = ''
    material: str = ''
    thickness: float = 0.0
    repetitions: int = 0
    height: float = 0.0
    width: float = 0.0
    job_number: str = ''
    prog_number: int = 0
    type: int = -1
    sheets: int = 0
    heads: int = 0
    part_indexes: List[List[int]] = field(default_factory=list)


@dataclass
class Segment:
    """Structure for segment information"""
    type: int = -1  # 0:noCut linear; 1: linear; 2: CW Arc; 3: CCW Arc
    subtype: int = -1  # B parameter
    initial_pos: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    final_pos: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    arc_center_off: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    arc_center: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    arc_sense: int = 0  # 1: CW; -1: CCW
    power: float = -1.0  # [0,100] Laser power (Q parameter)
    points: List[List[float]] = field(default_factory=list)
    orientation: float = 0.0
    length: float = 0.0


@dataclass
class Contour:
    """Structure for contour information"""
    segments: List[Segment] = field(default_factory=list)
    total_segments: int = 0
    type: int = -1  # 0: outer contour; 1: inner contour
    points: List[List[float]] = field(default_factory=list)
    entrance_segment: List[Segment] = field(default_factory=list)
    sense: int = 0


@dataclass
class Part:
    """Structure for part information"""
    contours: List[Contour] = field(default_factory=list)
    area: float = 0.0
    gravity_center: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    delaunay_tri: Optional[Any] = None
    convex_hull: Optional[Any] = None
    voronoi_v: List[List[float]] = field(default_factory=list)
    voronoi_r: List[float] = field(default_factory=list)
    total_contours: int = 0
    global_part_counter: int = 0
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    vangle_2d: float = 0.0
    rotation_point: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class PartReference:
    """Structure for part reference information"""
    total_ref_parts: int = 0
    parts: List[Part] = field(default_factory=list)
    ref_name: str = ''


def process_header(tline: str, cutting_unit: CuttingUnit) -> CuttingUnit:
    """Process header information from G-code file"""
    split_line = tline.split(':')
    
    if len(split_line) < 2:
        return cutting_unit
    
    header_type = split_line[0]
    content = split_line[1]
    
    # Find closing parenthesis
    close_paren = content.find(' )')
    if close_paren > 0:
        value = content[2:close_paren].strip()
    else:
        return cutting_unit
    
    # Skip empty values
    if not value:
        return cutting_unit
    
    try:
        if header_type == '( MACHINE ':
            cutting_unit.machine = value
        elif header_type == '( MATERIAL ':
            cutting_unit.material = value
        elif header_type == '( THICKNESS ':
            cutting_unit.thickness = float(value)
        elif header_type == '( REPETITIONS ':
            cutting_unit.repetitions = int(value)
        elif header_type == '( FORMAT ':
            format_parts = value.split('x')
            if len(format_parts) == 2:
                cutting_unit.height = float(format_parts[0])
                cutting_unit.width = float(format_parts[1])
        elif header_type == '( JOB NUMBER ':
            cutting_unit.job_number = value
        elif header_type == '( PROGRAM NUMBER ':
            cutting_unit.prog_number = int(value)
        elif header_type == '( TYPE ':
            cutting_unit.type = int(value)
        elif header_type == '( NUMBER OF SHEETS ':
            cutting_unit.sheets = int(value)
        elif header_type == '( CUTTING HEADS ':
            cutting_unit.heads = int(value)
    except (ValueError, TypeError) as e:
        # Skip malformed header values
        pass
    
    return cutting_unit


def process_part_info(tline: str, part_references: List[PartReference], 
                     cutting_unit: CuttingUnit, ref_index: int, part_index: int, 
                     filepath: str) -> Tuple[int, int, List[PartReference], CuttingUnit]:
    """Process part information from G-code file"""
    
    if len(tline) < 2:
        return ref_index, part_index, part_references, cutting_unit
    
    if tline[:2] == '(P':
        try:
            split_line = tline.split(':')
            if len(split_line) < 3:
                return ref_index, part_index, part_references, cutting_unit
            
            # Extract part global index - handle empty strings
            # Format is (P1:ID1:...) so we need to extract the number after P
            part_str = split_line[0][2:].strip()  # Remove "(P" prefix
            if not part_str:
                return ref_index, part_index, part_references, cutting_unit
            part_global_index = int(part_str) - 1  # Convert to 0-based index
            
            # Extract ref index from ID field - handle empty strings  
            id_str = split_line[1][2:].strip()  # Remove "ID" prefix
            if not id_str:
                return ref_index, part_index, part_references, cutting_unit
            ref_index = int(id_str) - 1  # Convert to 0-based index
            
            close_paren = split_line[2].find(')')
            if close_paren == -1:
                close_paren = len(split_line[2])
            
            # Extract reference name
            ref_name = split_line[2][:close_paren].strip()
            
            # Ensure part_references has enough elements
            while len(part_references) <= ref_index:
                part_references.append(PartReference(parts=[Part()]))
            
            # Set reference name if not already set
            if not part_references[ref_index].ref_name:
                if not ref_name:
                    # Generate default name
                    file_parts = Path(filepath).stem
                    import datetime
                    timestamp = datetime.datetime.now().strftime('%H:%M:%S:%f')[:-3]
                    part_references[ref_index].ref_name = f"{file_parts}_NoRefName_{timestamp}"
                else:
                    part_references[ref_index].ref_name = ref_name
            
            # Add new part to this reference
            part_index = part_references[ref_index].total_ref_parts
            part_references[ref_index].total_ref_parts += 1
            
            # Ensure we have enough parts in the list
            while len(part_references[ref_index].parts) <= part_index:
                part_references[ref_index].parts.append(Part())
            
            # Ensure part_indexes has enough elements
            while len(cutting_unit.part_indexes) <= part_global_index:
                cutting_unit.part_indexes.append([0, 0])
            
            cutting_unit.part_indexes[part_global_index] = [ref_index, part_index]
                
        except (ValueError, IndexError) as e:
            # Skip malformed part info lines
            pass
    
    elif tline[:2] == '(X':
        try:
            # Parse X, Y, R values
            import re
            matches = re.findall(r'([XYR])([-+]?\d*\.?\d+)', tline)
            
            # Ensure we have valid indices
            if ref_index < len(part_references) and part_index < len(part_references[ref_index].parts):
                for match in matches:
                    coord, value = match
                    if value.strip():  # Only process non-empty values
                        if coord == 'X':
                            part_references[ref_index].parts[part_index].rotation_point[0] = float(value)
                        elif coord == 'Y':
                            part_references[ref_index].parts[part_index].rotation_point[1] = float(value)
                        elif coord == 'R':
                            part_references[ref_index].parts[part_index].vangle_2d = float(value) * math.pi / 180
        except (ValueError, IndexError) as e:
            # Skip malformed coordinate lines
            pass
    
    return ref_index, part_index, part_references, cutting_unit


def process_segment_info(tline: str, current_pos: List[float], 
                        current_quality: int) -> Tuple[Segment, List[float], int]:
    """Process segment information from G-code line"""
    
    segment = Segment()
    
    # Parse the line using regex
    import re
    tokens = re.findall(r'([GBXYZIJQE])([-+]?\d*\.?\d+)', tline)
    
    # Filter out empty values
    tokens = [(coord, value) for coord, value in tokens if value.strip()]
    
    # Check if it's a G65 command (quality change)
    g_commands = [token for token in tokens if token[0] == 'G']
    if g_commands and g_commands[0][1] == '65':
        for token in tokens:
            if token[0] == 'B':
                try:
                    current_quality = int(float(token[1]))
                except ValueError:
                    pass
        return segment, current_pos, current_quality
    
    # Process regular G command
    segment.subtype = current_quality
    
    if g_commands:
        try:
            segment.type = int(float(g_commands[0][1]))
            
            if segment.type == 2:
                segment.arc_sense = 1
            elif segment.type == 3:
                segment.arc_sense = -1
        except ValueError:
            segment.type = -1
    
    segment.initial_pos = current_pos.copy()
    
    for token in tokens:
        coord, value = token
        try:
            if coord == 'X':
                segment.final_pos[0] = float(value)
            elif coord == 'Y':
                segment.final_pos[1] = float(value)
            elif coord == 'Z':
                segment.final_pos[2] = float(value)
            elif coord == 'I':
                segment.arc_center_off[0] = float(value)
            elif coord == 'J':
                segment.arc_center_off[1] = float(value)
            elif coord == 'Q':
                segment.power = float(value)
        except ValueError:
            # Skip invalid numeric values
            continue
    
    # Calculate arc center
    segment.arc_center = [
        segment.initial_pos[0] + segment.arc_center_off[0],
        segment.initial_pos[1] + segment.arc_center_off[1],
        segment.initial_pos[2] + segment.arc_center_off[2]
    ]
    
    current_pos = segment.final_pos.copy()
    
    return segment, current_pos, current_quality


def remove_entrance_segments(contour: Contour, entrance_point_distance: float = 1.0) -> Tuple[Contour, List[int]]:
    """Remove entrance segments from contour"""
    
    entrance_segment_indices = []
    total_segments = contour.total_segments
    
    if total_segments <= 1:
        return contour, entrance_segment_indices
    
    contour_final_point = contour.segments[total_segments - 1].final_pos
    
    if total_segments == 2:
        segment1_final_point = contour.segments[0].final_pos
        v1 = np.array(segment1_final_point) - np.array(contour_final_point)
        v1_mod = np.linalg.norm(v1)
        
        if v1_mod < entrance_point_distance:
            contour.entrance_segment = [contour.segments[0]]
            contour.segments = contour.segments[1:]
            contour.total_segments = total_segments - 1
            entrance_segment_indices = [0]
    
    else:
        segment1_final_point = contour.segments[0].final_pos
        segment2_final_point = contour.segments[1].final_pos
        
        v1 = np.array(segment1_final_point) - np.array(contour_final_point)
        v2 = np.array(segment2_final_point) - np.array(contour_final_point)
        
        v1_mod = np.linalg.norm(v1)
        v2_mod = np.linalg.norm(v2)
        
        min_mod = min(v1_mod, v2_mod)
        min_index = 0 if v1_mod < v2_mod else 1
        
        if min_mod < entrance_point_distance:
            contour.entrance_segment = contour.segments[:min_index + 1]
            contour.segments = contour.segments[min_index + 1:]
            contour.total_segments = total_segments - (min_index + 1)
            entrance_segment_indices = list(range(min_index + 1))
    
    return contour, entrance_segment_indices


def calc_contour_sense(total_segments: int, segments: List[Segment]) -> Tuple[float, int, List[Segment]]:
    """Calculate contour sense (CW or CCW)"""
    
    if total_segments == 1:
        # Single segment - must be a circle
        center_pos = np.array(segments[0].initial_pos) + np.array(segments[0].arc_center_off)
        
        v1 = np.array(segments[0].initial_pos[:2]) - center_pos[:2]
        v2 = np.array(segments[0].final_pos[:2]) - center_pos[:2]
        
        angle_1 = math.atan2(v1[1], v1[0])
        angle_2 = math.atan2(v2[1], v2[0])
        
        if segments[0].type == 2:  # CW
            if angle_2 > angle_1:
                angle_2 = angle_2 - 2 * math.pi
        elif segments[0].type == 3:  # CCW
            if angle_2 < angle_1:
                angle_2 = angle_2 + 2 * math.pi
        
        contour_sum_orientation = angle_2 - angle_1
        segments[0].orientation = angle_1
    
    else:
        # Multiple segments
        vector1 = []
        
        for i in range(total_segments):
            v = np.array(segments[i].final_pos) - np.array(segments[i].initial_pos)
            angle_1 = math.atan2(v[1], v[0])
            
            if angle_1 < 0:
                angle_1 = 2 * math.pi + angle_1
            
            vector1.append(angle_1)
            segments[i].orientation = angle_1
        
        # Calculate angle differences
        diff_vector = []
        for i in range(len(vector1)):
            next_i = (i + 1) % len(vector1)
            diff = vector1[next_i] - vector1[i]
            diff_vector.append(diff)
        
        # Put differences in [-pi, pi] range
        diff_vector_pi = [math.atan2(math.sin(d), math.cos(d)) for d in diff_vector]
        
        contour_sum_orientation = sum(diff_vector_pi)
    
    contour_sense = CCW if contour_sum_orientation > 0 else CW
    
    return contour_sum_orientation, contour_sense, segments


def tci_move_points(points: np.ndarray, offset: np.ndarray, angle_2d: float, 
                   rotation_point: np.ndarray) -> np.ndarray:
    """Move points with rotation and translation"""
    
    # Rotation matrix
    cos_a = math.cos(angle_2d)
    sin_a = math.sin(angle_2d)
    r_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    
    # Ensure points is 2D
    if points.ndim == 1:
        points = points.reshape(1, -1)
    
    # Apply transformation
    centered_points = points[:, :2] - rotation_point[:2]
    rotated_points = (r_mat @ centered_points.T).T
    moved_points = rotated_points + offset[:2]
    
    return moved_points


def tci_gcode_reader(filepath: str) -> Tuple[List[PartReference], CuttingUnit, int]:
    """Main G-code reader function"""
    
    # Initialize structures
    cutting_unit = CuttingUnit()
    part_references = [PartReference(parts=[Part()])]
    
    # Initialize processing variables
    current_pos = [0.0, 0.0, 0.0]
    current_quality = 0
    header_flag = True
    new_contour_flag = True
    ref_index = 0
    part_index = 0
    
    try:
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                # Process header
                if header_flag:
                    cutting_unit = process_header(line, cutting_unit)
                
                # Process part info
                ref_index, part_index, part_references, cutting_unit = process_part_info(
                    line, part_references, cutting_unit, ref_index, part_index, filepath
                )
                
                # Process instruction lines
                if line.startswith('N'):
                    header_flag = False
                    
                    # Extract G-code part
                    space_idx = line.find(' ')
                    if space_idx > 0:
                        gcode_line = line[space_idx + 1:]
                    else:
                        continue
                    
                    # Process G instructions
                    if gcode_line.startswith('G'):
                        segment, current_pos, current_quality = process_segment_info(
                            gcode_line, current_pos, current_quality
                        )
                        
                        # Check if segment is cutting
                        if (segment.type == 0 or segment.subtype == 4 or 
                            segment.subtype == 5 or (segment.subtype == 6 and segment.power < 1)):
                            new_contour_flag = True
                        
                        elif segment.type > 0:
                            # Ensure we have enough parts
                            while len(part_references) <= ref_index:
                                part_references.append(PartReference(parts=[Part()]))
                            
                            while len(part_references[ref_index].parts) <= part_index:
                                part_references[ref_index].parts.append(Part())
                            
                            if new_contour_flag:
                                new_contour_flag = False
                                part_references[ref_index].parts[part_index].total_contours += 1
                                contour_index = part_references[ref_index].parts[part_index].total_contours - 1
                                
                                # Ensure contours list is long enough
                                while len(part_references[ref_index].parts[part_index].contours) <= contour_index:
                                    part_references[ref_index].parts[part_index].contours.append(Contour())
                                
                                part_references[ref_index].parts[part_index].contours[contour_index].total_segments = 1
                            else:
                                part_references[ref_index].parts[part_index].contours[contour_index].total_segments += 1
                            
                            segment_index = part_references[ref_index].parts[part_index].contours[contour_index].total_segments - 1
                            
                            # Ensure segments list is long enough
                            while len(part_references[ref_index].parts[part_index].contours[contour_index].segments) <= segment_index:
                                part_references[ref_index].parts[part_index].contours[contour_index].segments.append(Segment())
                            
                            part_references[ref_index].parts[part_index].contours[contour_index].segments[segment_index] = segment
    
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    
    n_references = len(part_references)
    return part_references, cutting_unit, n_references


def tci_process_parts(part_references: List[PartReference], 
                     entrance_point_distance: float = 1.0) -> List[PartReference]:
    """Process parts to remove entrance segments and calculate contour properties"""
    
    n_references = len(part_references)
    
    for i in range(n_references):
        total_ref_parts = part_references[i].total_ref_parts
        if not part_references[i].parts:
            continue
            
        total_contours = part_references[i].parts[0].total_contours
        
        for k in range(total_ref_parts):
            if k >= len(part_references[i].parts):
                continue
                
            for h in range(total_contours):
                if h >= len(part_references[i].parts[k].contours):
                    continue
                
                # Remove entrance segments
                part_references[i].parts[k].contours[h], _ = remove_entrance_segments(
                    part_references[i].parts[k].contours[h], entrance_point_distance
                )
                
                # Set contour type
                if h == total_contours - 1:
                    part_references[i].parts[k].contours[h].type = OUTER_CONT
                else:
                    part_references[i].parts[k].contours[h].type = INNER_CONT
                
                # Calculate contour sense
                total_segments = part_references[i].parts[k].contours[h].total_segments
                if total_segments > 0:
                    _, sense, segments = calc_contour_sense(
                        total_segments, part_references[i].parts[k].contours[h].segments
                    )
                    part_references[i].parts[k].contours[h].sense = sense
                    part_references[i].parts[k].contours[h].segments = segments
    
    return part_references


def matlab2_sorting_bounding_box(matlab_bounding_box: np.ndarray) -> np.ndarray:
    """Convert MATLAB bounding box to sorting bounding box"""
    
    x_min = min(matlab_bounding_box[0, 0], matlab_bounding_box[1, 0])
    x_max = max(matlab_bounding_box[0, 0], matlab_bounding_box[1, 0])
    y_min = min(matlab_bounding_box[0, 1], matlab_bounding_box[1, 1])
    y_max = max(matlab_bounding_box[0, 1], matlab_bounding_box[1, 1])
    
    # Follow MATLAB logic: different order based on width vs height
    if (x_max - x_min) >= (y_max - y_min):
        # Width >= Height: standard order
        sorting_bounding_box = np.array([
            [x_min, y_min],
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max]
        ])
    else:
        # Height > Width: rotated order
        sorting_bounding_box = np.array([
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max],
            [x_min, y_min]
        ])
    
    return sorting_bounding_box


def generate_contour_points(contour, dist_res):
    """
    Generates interpolated points along a contour based on its segments.
    Adapted for Contour dataclass objects from load_slot module.
    
    Args:
        contour: Contour object containing segments
        dist_res: Distance resolution for point interpolation
    
    Returns:
        numpy array: Generated points for the contour
    """
    points_list = []
    
    # Access segments from the Contour object
    segments = contour.segments
    total_segments = contour.total_segments
    
    for i in range(total_segments):
        segment = segments[i]
        seg_type = segment.type
        
        if seg_type == 1:  # Line segment
            initial_pos = np.array(segment.initial_pos)
            final_pos = np.array(segment.final_pos)
            vector = final_pos - initial_pos
            dist = np.linalg.norm(vector)
            
            if dist > 0:
                dire = vector / dist
                n_gaps = int(np.floor(dist / dist_res))
                
                if n_gaps > 0:
                    distances = np.linspace(0, dist - dist_res, n_gaps)
                else:
                    distances = np.array([0])
                
                interp_pos = initial_pos + dire * distances[:, np.newaxis]
            else:
                interp_pos = initial_pos.reshape(1, -1)
                
        elif seg_type == 2:  # Arc segment (clockwise)
            initial_pos = np.array(segment.initial_pos)
            final_pos = np.array(segment.final_pos)
            arc_center_off = np.array(segment.arc_center_off)
            
            center_pos = initial_pos + arc_center_off
            
            v1 = initial_pos[:2] - center_pos[:2]
            v2 = final_pos[:2] - center_pos[:2]
            
            r = np.linalg.norm(v2)
            angle_1 = np.arctan2(v1[1], v1[0])
            angle_2 = np.arctan2(v2[1], v2[0])
            
            if angle_2 >= angle_1:
                angle_2 = angle_2 - 2 * np.pi
            
            angles = np.array([angle_1])
            Z_col = final_pos[2]
            
            if (dist_res <= (2 * r)) and (r > 0):
                angular_res_aux = 2 * np.arcsin(dist_res / (2 * r))
                n_gaps = int(np.floor(abs(angle_2 - angle_1) / angular_res_aux))
                
                if n_gaps > 1:
                    angles = np.linspace(angle_1, angle_2, n_gaps + 1)
                    angles = angles[:n_gaps]
                    Z_col = np.linspace(center_pos[2], final_pos[2], n_gaps)
            
            aux_points = center_pos[:2] + r * np.column_stack([np.cos(angles), np.sin(angles)])
            
            if isinstance(Z_col, (int, float)):
                Z_col = np.full(len(angles), Z_col)
            
            interp_pos = np.column_stack([aux_points, Z_col])
            
        elif seg_type == 3:  # Arc segment (counterclockwise)
            initial_pos = np.array(segment.initial_pos)
            final_pos = np.array(segment.final_pos)
            arc_center_off = np.array(segment.arc_center_off)
            
            center_pos = initial_pos + arc_center_off
            
            v1 = initial_pos[:2] - center_pos[:2]
            v2 = final_pos[:2] - center_pos[:2]
            
            r = np.linalg.norm(v2)
            angle_1 = np.arctan2(v1[1], v1[0])
            angle_2 = np.arctan2(v2[1], v2[0])
            
            if angle_2 <= angle_1:
                angle_2 = angle_2 + 2 * np.pi
            
            angles = np.array([angle_1])
            Z_col = final_pos[2]
            
            if (dist_res <= (2 * r)) and (r > 0):
                angular_res_aux = 2 * np.arcsin(dist_res / (2 * r))
                n_gaps = int(np.floor(abs(angle_2 - angle_1) / angular_res_aux))
                
                if n_gaps > 1:
                    angles = np.linspace(angle_1, angle_2, n_gaps + 1)
                    angles = angles[:n_gaps]
                    Z_col = np.linspace(center_pos[2], final_pos[2], n_gaps)
            
            aux_points = center_pos[:2] + r * np.column_stack([np.cos(angles), np.sin(angles)])
            
            if isinstance(Z_col, (int, float)):
                Z_col = np.full(len(angles), Z_col)
            
            interp_pos = np.column_stack([aux_points, Z_col])
        
        else:
            continue
        
        points_list.append(interp_pos)
    
    # Concatenate all points
    if points_list:
        return np.vstack(points_list)
    else:
        return np.array([]).reshape(0, 3)


def build_polygon_chains_from_constraints(constraints, points):
    """
    Builds closed polygon chains from constraints (edges).
    The constraints define the polygon borders and its holes.
    
    Args:
        constraints: Array of constraints (edges) (N x 2)
        points: Array of points (M x 2)
    
    Returns:
        list: List of polygons (Polygon objects)
    """
    # Create connection graph
    graph = defaultdict(list)
    for edge in constraints:
        graph[edge[0]].append(edge[1])
        graph[edge[1]].append(edge[0])
    
    visited = set()
    chains = []
    
    # Find all closed chains
    for start in range(len(points)):
        if start in visited or start not in graph:
            continue
        
        chain = [start]
        visited.add(start)
        current = start
        
        # Follow the chain
        while True:
            neighbors = [n for n in graph[current] if n not in visited or (n == start and len(chain) > 2)]
            if not neighbors:
                break
            
            next_node = neighbors[0]
            if next_node == start and len(chain) > 2:
                chains.append(chain)
                break
            
            if next_node in visited:
                break
                
            chain.append(next_node)
            visited.add(next_node)
            current = next_node
    
    # Convert chains to polygons
    polygons = []
    for chain in chains:
        if len(chain) >= 3:
            poly_points = [points[i] for i in chain]
            try:
                poly = Polygon(poly_points)
                if poly.is_valid:
                    polygons.append(poly)
            except:
                continue
    
    return polygons


def is_interior_triangle(tri, points, constraint_polygons):
    """
    Determines if a triangle is inside the polygon.
    A triangle is interior if its centroid is inside the exterior polygon
    but outside all holes.
    
    Args:
        tri: Triangle indices
        points: Array of points
        constraint_polygons: List of polygons [exterior, hole1, hole2, ...]
    
    Returns:
        bool: True if the triangle is interior
    """
    if not constraint_polygons:
        return False
    
    # Calculate triangle centroid
    centroid = np.mean(points[tri], axis=0)
    point = Point(centroid)
    
    # The largest polygon is the exterior
    exterior = constraint_polygons[0]
    
    # Check if it's inside the exterior
    if not exterior.contains(point):
        return False
    
    # Check that it's not inside any hole
    for hole_poly in constraint_polygons[1:]:
        if hole_poly.contains(point):
            return False
    
    return True


def boundingbox(polygon):
    """
    Calculates the bounding box of a polygon.
    Equivalent to polyout.boundingbox in MATLAB.
    
    Returns:
        tuple: (xlim, ylim) where each is [min, max]
    """
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    xlim = [bounds[0], bounds[2]]
    ylim = [bounds[1], bounds[3]]
    return xlim, ylim


def extract_boundary_from_triangulation(triangles, points):
    """
    Extracts the boundary of a triangulation, including interior holes.
    Replicates the behavior of MATLAB's boundaryshape(TR).
    
    Args:
        triangles: Array of triangles (N x 3)
        points: Array of points (M x 2)
    
    Returns:
        Shapely Polygon or MultiPolygon with interior holes
    """
    from collections import defaultdict
    
    # Find all edges and count how many times each appears
    edge_count = defaultdict(int)
    
    for tri in triangles:
        # Each triangle has 3 edges
        edges = [
            tuple(sorted([tri[0], tri[1]])),
            tuple(sorted([tri[1], tri[2]])),
            tuple(sorted([tri[2], tri[0]]))
        ]
        for edge in edges:
            edge_count[edge] += 1
    
    # Boundary edges appear only once
    boundary_edges = [edge for edge, count in edge_count.items() if count == 1]
    
    if not boundary_edges:
        return None
    
    # Build chains of connected edges (can be multiple loops)
    def build_chains(edges):
        """Builds closed chains from edges."""
        edges_dict = defaultdict(list)
        for e in edges:
            edges_dict[e[0]].append(e[1])
            edges_dict[e[1]].append(e[0])
        
        chains = []
        visited_edges = set()
        
        for start_edge in edges:
            if start_edge in visited_edges:
                continue
            
            # Try to build a chain from this edge
            chain = [start_edge[0], start_edge[1]]
            visited_edges.add(start_edge)
            visited_edges.add((start_edge[1], start_edge[0]))
            
            current = start_edge[1]
            
            while True:
                # Find the next connected point
                next_points = [p for p in edges_dict[current] if p not in chain[:-1] or p == chain[0]]
                
                if not next_points:
                    break
                
                next_point = next_points[0]
                
                # If we returned to the start, close the loop
                if next_point == chain[0]:
                    chains.append(chain)
                    break
                
                edge = tuple(sorted([current, next_point]))
                if edge in visited_edges:
                    break
                
                visited_edges.add(edge)
                visited_edges.add((edge[1], edge[0]))
                chain.append(next_point)
                current = next_point
            
        return chains
    
    chains = build_chains(boundary_edges)
    
    if not chains:
        return None
    
    # Convert chains to polygons
    polygons = []
    for chain in chains:
        if len(chain) >= 3:
            poly_points = [points[i] for i in chain]
            try:
                poly = Polygon(poly_points)
                if poly.is_valid:
                    polygons.append(poly)
            except:
                continue
    
    if not polygons:
        return None
    
    # Sort by area (largest is the exterior)
    polygons.sort(key=lambda p: p.area, reverse=True)
    
    if len(polygons) == 1:
        return polygons[0]
    
    # The largest polygon is the exterior, the rest are holes
    exterior = polygons[0]
    holes = []
    
    for hole_poly in polygons[1:]:
        # Verify that the hole is inside the exterior
        if exterior.contains(hole_poly) or exterior.intersects(hole_poly):
            holes.append(hole_poly.exterior.coords[:-1])  # Exclude the last duplicate point
    
    # Create polygon with holes
    if holes:
        return Polygon(exterior.exterior.coords, holes=holes)
    else:
        return exterior


def plot_delaunay_triangulation(polyout, P, interior_triangles, delaunayCheck):
    """
    Visualize the Delaunay triangulation with polygon and holes.
    Also displays the bounding box of the polygon.
    
    Args:
        polyout: Shapely Polygon with holes
        P: Array of points (M x 2)
        interior_triangles: Array of interior triangle indices
        delaunayCheck: Integer flag indicating valid triangulation
    """
    if polyout is None:
        print("Could not create output polygon")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Left panel: Polygon with holes and bounding box
    x, y = polyout.exterior.xy
    ax1.plot(x, y, 'b-', linewidth=2, label='Exterior')
    ax1.fill(x, y, alpha=0.3, color='blue')
    
    # Plot interior holes
    if hasattr(polyout, 'interiors') and len(polyout.interiors) > 0:
        for i, interior in enumerate(polyout.interiors):
            xi, yi = interior.xy
            ax1.plot(xi, yi, 'r-', linewidth=2, label=f'Hole {i+1}' if i == 0 else '')
            ax1.fill(xi, yi, alpha=0.5, color='white')
    
    # Plot bounding box
    bounds = polyout.bounds  # (minx, miny, maxx, maxy)
    bbox_x = [bounds[0], bounds[2], bounds[2], bounds[0], bounds[0]]
    bbox_y = [bounds[1], bounds[1], bounds[3], bounds[3], bounds[1]]
    ax1.plot(bbox_x, bbox_y, 'g--', linewidth=2, label='Bounding Box')
    
    # Add bounding box coordinates as text
    bbox_text = f"BBox: X=[{bounds[0]:.2f}, {bounds[2]:.2f}]\nY=[{bounds[1]:.2f}, {bounds[3]:.2f}]"
    ax1.text(0.02, 0.98, bbox_text, transform=ax1.transAxes,
             fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_title(f'Resulting Polygon (delaunayCheck = {delaunayCheck})')
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    
    # Right panel: Triangulation
    if interior_triangles is not None and len(interior_triangles) > 0:
        ax2.triplot(P[:, 0], P[:, 1], interior_triangles, 'g-', alpha=0.4, linewidth=0.5)
        ax2.plot(P[:, 0], P[:, 1], 'ro', markersize=2, alpha=0.5)
        ax2.set_aspect('equal')
        ax2.grid(True, alpha=0.3)
        ax2.set_title('Interior Delaunay Triangulation')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
    
    plt.tight_layout()
    plt.show()
    
    print(f"\ndelaunayCheck = {delaunayCheck}")
    num_holes = len(polyout.interiors) if hasattr(polyout, 'interiors') else 0
    print(f"Number of interior holes: {num_holes}")
    bounds = polyout.bounds
    print(f"Bounding Box: X=[{bounds[0]:.2f}, {bounds[2]:.2f}], Y=[{bounds[1]:.2f}, {bounds[3]:.2f}]")


def circumcenter_triangles(triangles: np.ndarray, points: np.ndarray) -> np.ndarray:
    """
    Calculate the circumcenter of each triangle in the triangulation.
    
    The circumcenter is the point equidistant from all three vertices of a triangle.
    For a triangle with vertices (x1, y1), (x2, y2), (x3, y3), the circumcenter is calculated
    using the formula derived from the perpendicular bisectors of the sides.
    
    Args:
        triangles: Array of triangle indices (N x 3)
        points: Array of point coordinates (M x 2)
    
    Returns:
        circumcenters: Array of circumcenter coordinates (N x 2)
    """
    n_triangles = len(triangles)
    circumcenters = np.zeros((n_triangles, 2))
    
    for i, tri in enumerate(triangles):
        # Get the three vertices of the triangle
        p1 = points[tri[0]]
        p2 = points[tri[1]]
        p3 = points[tri[2]]
        
        # Convert to homogeneous coordinates for circumcenter calculation
        ax, ay = p1[0], p1[1]
        bx, by = p2[0], p2[1]
        cx, cy = p3[0], p3[1]
        
        # Calculate the circumcenter using the determinant method
        # Based on the formula for circumcenter of a triangle
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        
        if abs(D) < 1e-10:
            # Degenerate triangle - use centroid as fallback
            circumcenters[i] = np.array([(ax + bx + cx) / 3, (ay + by + cy) / 3])
        else:
            ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / D
            uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / D
            
            circumcenters[i] = np.array([ux, uy])
    
    return circumcenters


def find_main_reference(reference: int, part_references: List[PartReference]) -> Tuple[np.ndarray, int, int]:
    """
    Find the first valid main reference part and compute its Delaunay triangulation bounding box.
    
    Returns:
        Tuple of (ref_bounding_box, ref_part, computable, polyout)
    """
    main_ref_not_found = True
    ref_part = 0
    computable = 1
    ref_bounding_box = np.array([[0, 0], [1, 1]])  # Default fallback
    
    while main_ref_not_found and ref_part < len(part_references[reference].parts):

        parts_field = part_references[reference].parts[ref_part]
        
        # Access totalContours from the Part object (it's an attribute, not a nested field)
        totalCon = parts_field.total_contours
        dist_res = 3
        
        points = []
        contour_lengths = np.zeros(totalCon, dtype=int)
        
        # Access contours - it's a list in the Part object
        contours_field = parts_field.contours
        
        # Process all contours (1 to totalCon)
        for i in range(totalCon):
            contour = contours_field[i]
            
            # Generate contour points using the translated function
            contour_points = generate_contour_points(contour, dist_res)
            
            if len(contour_points) > 0:  # Only add non-empty arrays
                points.append(contour_points)
                contour_lengths[i] = len(contour_points)
        
        # Skip if no valid points were generated
        if not points:
            ref_part += 1
            continue
        
        # Combine all points
        points = np.vstack(points)
        
        # Filter contour_lengths to match actual processed contours
        contour_lengths = contour_lengths[contour_lengths > 0]
        
        # Calculate cumulative indices
        contour_indices = np.cumsum(contour_lengths)
        
        # Extract P (first 2 columns)
        P = points[:, :2]
        
        # Build Const (constraints) - matching MATLAB logic
        # First contour
        Const = []
        for j in range(contour_indices[0] - 1):
            Const.append([j, j + 1])
        Const.append([contour_indices[0] - 1, 0])  # Close first contour
        
        # Remaining contours
        for i in range(1, len(contour_indices)):
            start_idx = contour_indices[i - 1]
            end_idx = contour_indices[i]
            for j in range(start_idx, end_idx - 1):
                Const.append([j, j + 1])
            Const.append([end_idx - 1, start_idx])  # Close contour
        
        Const = np.array(Const)
        
        # Build polygons from constraints
        # This gives us the exterior polygon and interior holes
        constraint_polygons = build_polygon_chains_from_constraints(Const, P)
        
        # Sort by area (largest is the exterior)
        constraint_polygons.sort(key=lambda p: p.area, reverse=True)
        
        print(f"Polygons found: {len(constraint_polygons)}")
        if constraint_polygons:
            print(f"  Exterior: area = {constraint_polygons[0].area:.2f}")
            for i, poly in enumerate(constraint_polygons[1:]):
                print(f"  Hole {i+1}: area = {poly.area:.2f}")
        
        # DT = delaunayTriangulation(P, Const);
        # In Python, we use scipy.spatial.Delaunay
        DT = Delaunay(P)
        
        delaunayCheck = 0
        polyout = None
        
        # if ~isempty(DT.ConnectivityList)
        if DT.simplices is not None and len(DT.simplices) > 0:
            # TF = isInterior(DT);
            # Filter triangles that are in the interior
            TF = np.array([is_interior_triangle(tri, P, constraint_polygons) for tri in DT.simplices])
            
            print(f"\nTotal triangles: {len(DT.simplices)}")
            print(f"Interior triangles: {np.sum(TF)}")
            
            # if (DT.ConnectivityList(TF,:) <= length(P))
            interior_triangles = DT.simplices[TF]

            if len(interior_triangles) > 0 and np.all(interior_triangles < len(P)):
                # TR = triangulation(DT.ConnectivityList(TF,:), P);
                # polyout = boundaryshape(TR);
                # In MATLAB, boundaryshape(TR) returns the polygon with holes
                # which is exactly what we already have in constraint_polygons
                # Create polygon with holes from constraint_polygons
                if len(constraint_polygons) > 0:
                    exterior = constraint_polygons[0]
                    holes = [list(poly.exterior.coords[:-1]) for poly in constraint_polygons[1:]]
                    
                    if holes:
                        polyout = Polygon(exterior.exterior.coords, holes=holes)
                    else:
                        polyout = exterior
                    
                    # [xlim, ylim] = polyout.boundingbox;
                    xlim, ylim = boundingbox(polyout)
                    
                    # if polyout.NumRegions == 1
                    # In Shapely, we check if it's a simple Polygon (not MultiPolygon)
                    if isinstance(polyout, Polygon) and not isinstance(polyout, MultiPolygon):
                        delaunayCheck = 1
                        # Calculate circumcenters of interior triangles
                        voronoi = circumcenter_triangles(interior_triangles, P)


        if delaunayCheck == 1:
            main_ref_not_found = False
            ref_bounding_box = np.array(polyout.bounds).reshape(2, 2)
            #plot_delaunay_triangulation(polyout, P, interior_triangles, delaunayCheck)
        else:
            ref_part += 1
    
    if main_ref_not_found:
        # Use fallback bounding box
        computable = 0
        ref_part = 0
        polyout = []
        voronoi = []
    
    return ref_bounding_box, ref_part, computable, polyout, voronoi



def load_slot(slot_file_lpp: str) -> int:
    """
    Main function to load and process TCI G-Code slot file.
    
    Args:
        slot_file_lpp: Path to the .lpp file
        
    Returns:
        error_flag: 0 = success, negative = error
    """
    
    error_flag = 0
    
    # Extract slot name
    slot_path = Path(slot_file_lpp)
    if not slot_path.exists():
        return -1  # Slot file not found
    
    slot_name = slot_path.stem
    
    try:
        print(f"Reading G-Code file: {slot_file_lpp}")
        # Process G-Code
        part_references, cutting_unit, n_references = tci_gcode_reader(slot_file_lpp)
        print(f"Found {n_references} references")
        
        print("Processing parts...")
        part_references = tci_process_parts(part_references)        
        
        # Process references from slot
        total_refs = len(part_references)
        ref_part_json = []
        part_json = []
        
        # Process references and parts following MATLAB order
        part_global_index = 0
        
        # First pass: Process references (for refPartJson)
        for reference in range(total_refs):
            # Calculate reference bounding box using helper function
            ref_bounding_box, ref_part, computable, polyout, voronoi = find_main_reference(reference, part_references)
            
            # Store reference data for later use
            ref_data = {
                'ref_name': part_references[reference].ref_name,
                'ref_bounding_box': ref_bounding_box,
                'ref_part_index': ref_part,
                'ref_angle': part_references[reference].parts[ref_part].vangle_2d,
                'ref_offset': np.array(part_references[reference].parts[ref_part].rotation_point[:2]),
                'ref_computable': computable,
            }
            
            # Process all parts for this reference (following MATLAB order)
            for part_index in range(part_references[reference].total_ref_parts):
                print(f"Processing part {part_global_index + 1}: ref={reference}, part={part_index}")
                
                # Get part transformation data
                part_data = part_references[reference].parts[part_index]
                part_offset = np.array(part_data.rotation_point[:2])
                part_angle = part_data.vangle_2d
                
                # Create reference sorting bounding box 4 points (same as MATLAB)
                ref_bounding_box_sorting = matlab2_sorting_bounding_box(ref_data['ref_bounding_box'])
                
                # Rotate and translate reference BoundingBox to part Bounding box (same as MATLAB)
                bounding_box_4pts = tci_move_points(ref_bounding_box_sorting, 
                                                  part_offset, 
                                                  part_angle - ref_data['ref_angle'], 
                                                  ref_data['ref_offset'])
                
                # Calculate angle based on bounding box (same as MATLAB)
                angle = math.atan2(bounding_box_4pts[1, 1] - bounding_box_4pts[0, 1], 
                                 bounding_box_4pts[1, 0] - bounding_box_4pts[0, 0])
                
                # Use the 4-point bounding box for partJson
                bounding_box = bounding_box_4pts.tolist()
                
                # Create part JSON entry
                part_entry = {
                    'reference': ref_data['ref_name'],
                    'boundingBox': bounding_box,  # Already a list of lists
                    'angle': angle
                }
                
                part_json.append(part_entry)
                print(f"  Added part: {ref_data['ref_name']} at angle {angle}")
                
                part_global_index += 1
        
            # Create refPartJson entries using the same logic as the first pass
            # Reference Angle and Offset for rotation and translation (same as MATLAB)
            total_con = part_references[reference].parts[ref_part].total_contours
            
            # Create sorting bounding box (4 points) - same as MATLAB
            bounding_box = matlab2_sorting_bounding_box(ref_bounding_box)
            
            # Calculate angle of part wrt bounding box (same as MATLAB)
            angle = math.atan2(bounding_box[1, 1] - bounding_box[0, 1], 
                                bounding_box[1, 0] - bounding_box[0, 0])
            
            # Create rotated zero bounding box (same as MATLAB)
            # rotatedZeroBoundingBox = tci_movePoints(boundingBox,[0 0], -angle, boundingBox(1,:));
            rotated_zero_bbox = tci_move_points(bounding_box, np.array([0, 0]), -angle, bounding_box[0])
            
            # Apply same transformation to polyout polygon using Shapely affinity
            # Equivalent to tci_move_points(polyout, [0,0], -angle, bounding_box[0])
            # 1. Translate so rotation point is at origin: subtract bounding_box[0]
            rotated_polyout = affinity.translate(polyout, xoff=-bounding_box[0][0], yoff=-bounding_box[0][1])
            
            # 2. Rotate by -angle around the origin
            rotated_polyout = affinity.rotate(rotated_polyout, -angle * 180 / np.pi, origin=(0, 0))
            
            # Rotate voronoi points
            rotated_voronoi = tci_move_points(voronoi, np.array([0, 0]), -angle, bounding_box[0])

            # Create reference JSON structure (same as MATLAB)
            ref_part_data = {
                'reference': part_references[reference].ref_name,
                'boundingBox': rotated_zero_bbox.tolist(),  # Use the rotated bounding box
                'angle': 0,  # Always 0 for reference as in MATLAB
                'computable': computable,
                'toolLocation': [],
                'toolActive': [],
                'thickness': cutting_unit.thickness,
                'material': cutting_unit.material,
                'geometry': {
                    'totalContours': total_con,
                    'contours': [],
                    'voronoi': rotated_voronoi,
                    'polyShape': rotated_polyout
                }
            }
            
            # Add detailed contour geometry (same as MATLAB)
            contours_list = []
            for i in range(total_con):
                if i < len(part_references[reference].parts[ref_part].contours):
                    contour = part_references[reference].parts[ref_part].contours[i]
                    
                    contour_data = {
                        'totalSegments': contour.total_segments,
                        'type': contour.type,
                        'sense': contour.sense
                    }
                    
                    # Add segments with transformed coordinates (same as MATLAB)
                    segments_list = []
                    for j in range(min(contour.total_segments, len(contour.segments))):
                        segment = contour.segments[j]
                        
                        # Apply tci_movePoints transformation like in MATLAB
                        # tci_movePoints(pos, [0 0], -angle, boundingBox(1,:))
                        initial_pos = tci_move_points(np.array([segment.initial_pos[:2]]), 
                                                    np.array([0, 0]), -angle, bounding_box[0])[0]
                        final_pos = tci_move_points(np.array([segment.final_pos[:2]]), 
                                                    np.array([0, 0]), -angle, bounding_box[0])[0]
                        arc_center = tci_move_points(np.array([segment.arc_center[:2]]), 
                                                    np.array([0, 0]), -angle, bounding_box[0])[0]
                        # For arcCenterOff, rotation point is [0,0] as in MATLAB
                        arc_center_off = tci_move_points(np.array([segment.arc_center_off[:2]]), 
                                                        np.array([0, 0]), -angle, np.array([0, 0]))[0]
                        
                        segment_data = {
                            'type': segment.type,
                            'initialPos': initial_pos.tolist(),
                            'finalPos': final_pos.tolist(),
                            'arcCenter': arc_center.tolist(),
                            'arcCenterOff': arc_center_off.tolist(),
                            'arcSense': segment.arc_sense
                        }
                        segments_list.append(segment_data)
                    
                    # MATLAB: single segment becomes object, multiple segments become array
                    if len(segments_list) == 1:
                        contour_data['segments'] = segments_list[0]
                    else:
                        contour_data['segments'] = segments_list
                    
                    contours_list.append(contour_data)
            
            # MATLAB: single contour becomes object, multiple contours become array
            if len(contours_list) == 1:
                ref_part_data['geometry']['contours'] = contours_list[0]
            else:
                ref_part_data['geometry']['contours'] = contours_list
            
            ref_part_json.append(ref_part_data)
        
        # Save JSON files
        ref_filename = f"refPartJson_{slot_name}.json"
        parts_filename = f"partJson_{slot_name}.json"
        
        # Serialize data to JSON-compatible format (converts Shapely to GeoJSON)
        ref_part_json_serialized = serialize_for_json(ref_part_json)
        part_json_serialized = serialize_for_json(part_json)
        
        with open(ref_filename, 'w') as f:
            json.dump(ref_part_json_serialized, f, indent=2)
        
        with open(parts_filename, 'w') as f:
            json.dump(part_json_serialized, f, indent=2)
        
        print(f"Files saved: {ref_filename}, {parts_filename}")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        error_flag = -99
    
    print(f"Error flag: {error_flag}")
    return error_flag


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python load_slot.py <slot_file.lpp>")
        sys.exit(1)
    
    slot_file = sys.argv[1]
    error_flag = load_slot(slot_file)
    sys.exit(error_flag)