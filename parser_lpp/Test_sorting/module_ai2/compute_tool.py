#!/usr/bin/env python3
"""
Compute_tool.py for direct processing tools.
"""

import json
import numpy as np
from shapely.geometry import Polygon


def compute_tool(input_file: str, output_file: str = None, n_points: int = 20):
    """
    Processes tool JSON and adds polygon data.
    
    Args:
        input_file: Input JSON file path
        output_file: Output JSON file path (optional)
        n_points: Number of points for circle approximation
    """
    # Load input data
    with open(input_file, 'r') as f:
        tools = json.load(f)
    
    # Process each tool
    for i, tool in enumerate(tools):
        diameter = tool['diameter']
        center = tool['position']
        
        # Generate circle points
        radius = diameter / 2.0
        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        
        points = np.column_stack([
            center[0] + radius * np.cos(angles),
            center[1] + radius * np.sin(angles)
        ])
        
        # Create polygon
        polygon = Polygon(points)
        
        # Add polygon data to tool
        tool['polygon'] = {
            "type": "Polygon",
            "coordinates": [points.tolist() + [points[0].tolist()]]  # Close the polygon
        }
        tool['area'] = polygon.area
        tool['bounds'] = polygon.bounds
        
        print(f"Tool {i+1}: diameter={diameter}, area={polygon.area:.2f}")
    
    # Save result
    if output_file is None:
        output_file = input_file.replace('.json', '_with_polygons.json')
    
    with open(output_file, 'w') as f:
        json.dump(tools, f, indent=2)
    
    print(f"Saved to: {output_file}")
    return tools


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python simple_compute_tool.py <input_file.json> [output_file.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    compute_tool(input_file, output_file)