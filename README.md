# Various Scripts
Different scripts and tools for Autocad, Civil 3D and more.

## LiDAR2C3D.py
This script processes massive LiDAR point clouds (e.g., .e57 files) into lightweight, bare-earth .las files ready for Civil 3D TIN surface creation.
It is specifically designed to bypass hardware limitations (like 16GB RAM limits) by splitting the workload:
- Phase 1: Spatial subsampling using CloudCompare (Memory-friendly decimation)
- Phase 2: Ground classification using PDAL's Cloth Simulation Filter (CSF)
