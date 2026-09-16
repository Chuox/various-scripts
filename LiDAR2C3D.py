"""
LiDAR to Civil 3D Bare-Earth Extraction Pipeline
Author: Jesus Duran | duran.ing and Gemini

This script processes massive LiDAR point clouds (e.g., .e57 files) into lightweight, 
bare-earth .las files ready for Civil 3D TIN surface creation. 
It is specifically designed to bypass hardware limitations (like 16GB RAM limits) 
by splitting the workload:
- Phase 1: Spatial subsampling using CloudCompare (Memory-friendly decimation)
- Phase 2: Ground classification using PDAL's Cloth Simulation Filter (CSF)
"""

import json
import subprocess
import os
import glob
from datetime import datetime

def run_cloudcompare_subsample(input_file, cc_path, output_dir):
    """
    Uses CloudCompare CLI to decimate the massive point cloud.
    We isolate the environments to prevent conflicts between Conda's Python 
    and CloudCompare's internal Python engine.
    """
    print(f"\n[PHASE 1] CloudCompare: Reading .e57 and subsampling to 0.1m...")
    
    # 1. Clone the current environment and strip Python paths to prevent CC crash window
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONHOME", None)
    clean_env.pop("PYTHONPATH", None)

    # CLI Command: -SS SPATIAL 0.1 reduces points to a minimum of 10cm distance
    cc_cmd = [
        cc_path,
        "-SILENT",
        "-O", input_file,
        "-SS", "SPATIAL", "0.1",
        "-C_EXPORT_FMT", "LAS",
        "-SAVE_CLOUDS"
    ]
    
    try:
        # 2. Execute CloudCompare with the clean environment
        subprocess.run(cc_cmd, check=True, env=clean_env)
        
        # CloudCompare saves the output in the source directory with a suffix. 
        # We need to locate it and move it to our designated temporary folder.
        original_dir = os.path.dirname(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        cc_output = glob.glob(os.path.join(original_dir, f"{base_name}*_SPATIAL_SUBSAMPLED*.las"))
        
        if not cc_output:
            raise FileNotFoundError("CloudCompare finished but couldn't find the output .las file.")
            
        final_cc_file = cc_output[0]
        new_path = os.path.join(output_dir, os.path.basename(final_cc_file))
        
        os.replace(final_cc_file, new_path)
        print(f"Phase 1 Complete. Lightweight .las saved to: {new_path}")
        return new_path
        
    except subprocess.CalledProcessError as e:
        print(f"\nCRITICAL ERROR in CloudCompare: {e}")
        raise

def run_pdal_csf(input_las, output_las):
    """
    Uses PDAL to extract the bare-earth ground model from the lightweight .las file 
    using a Cloth Simulation Filter (CSF).
    """
    print(f"\n[PHASE 2] PDAL: Running Cloth Simulation Filter (CSF)...")
    
    pipeline_dict = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": input_las
            },
            {
                # The CSF filter mathematically drops a simulated cloth onto the inverted point cloud
                "type": "filters.csf",
                "resolution": 0.5,
                # Rigidness controls cloth flexibility: 1 for rugged terrain, 2 for mixed, 3 for flat terrain
                "rigidness": 3
            },
            {
                # Keep only points classified as Ground (Class 2) by the CSF filter
                "type": "filters.range",
                "limits": "Classification[2:2]"
            },
            {
                # Final mathematical downsampling: creates a 0.5m perfect grid and snaps to the nearest real point
                "type": "filters.voxelcentroidnearestneighbor",
                "cell": 0.5
            },
            {
                "type": "writers.las",
                "filename": output_las
            }
        ]
    }
    
    temp_json = "temp_csf.json"
    # Ensure forward slashes for cross-platform compatibility
    pipeline_str = json.dumps(pipeline_dict, indent=4).replace('\\\\', '/')
    
    with open(temp_json, 'w') as f:
        f.write(pipeline_str)
        
    try:
        # Capture output prevents console spam and allows us to catch the exact internal error
        subprocess.run(['pdal', 'pipeline', temp_json], capture_output=True, text=True, check=True)
        print(f"Phase 2 Complete. Ground Surface saved to: {output_las}")
    except subprocess.CalledProcessError as e:
        print(f"\n--- PDAL INTERNAL ERROR ---")
        print(e.stderr)
        raise
    finally:
        # Clean up the temporary JSON file
        if os.path.exists(temp_json):
            os.remove(temp_json)

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"\n=== STARTING TWO-PHASE PROCESS: {start_time.strftime('%H:%M:%S')} ===")
    
    # 1. External Executables
    CC_EXE_PATH = r"C:\Program Files\CloudCompare\CloudCompare.exe"
    
    # 2. Project I/O Paths (Update these for your local machine)
    RAW_INPUT_FILE = r"D:\UPW-20260902-001\20 CADD\_Active\C3D_UPW-20260902-00\Existing\Survey Data\Ground_Points.e57"
    TEMP_DIR = r"D:\Scripts\LiDAR2C3D\Temp"
    FINAL_LAS = r"D:\Scripts\LiDAR2C3D\Final_Ground\Ground_Surface_C3D.las"
    
    # Ensure target directories exist before running
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(FINAL_LAS), exist_ok=True)
    
    try:
        # Phase 1: Memory-friendly spatial reduction
        light_las = run_cloudcompare_subsample(RAW_INPUT_FILE, CC_EXE_PATH, TEMP_DIR)
        
        # Phase 2: Ground extraction and final formatting
        run_pdal_csf(light_las, FINAL_LAS)
        
        print(f"\n=== SUCCESS! TOTAL TIME: {datetime.now() - start_time} ===")
    except Exception as e:
        print(f"\nProcess Aborted: {e}")