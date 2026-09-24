"""
Least-cost cable route for a wind farm grid connection - Gronau-Epe (NRW)
=========================================================================

Course exercise TÜ 4 "Kabeltrasse" (GIS-Akademie GmbH, "GIS and Geodata Expert"
continuing education program, Spatial Analyst module). The task, the cost
parameters and the scenario data (wind farm, connection points, contaminated
sites) were set by the course. Analysis and script: Carlo Piccillo, 2026.

This script records the workflow as it was run in the ArcGIS Pro GUI. It was
reconstructed from the ArcGIS Pro geoprocessing history (Copy Python Command):
tool calls and parameters are the ones actually used; paths were made relative,
the batch run was rewritten as a loop, and the environment settings used in the
session are set explicitly (the history copies did not include them).

Data are NOT included in the repository:
  - course data (uebung_04_kabeltrasse.gdb) belong to GIS-Akademie;
  - ALKIS and DTM are open data from Geobasis NRW (dl-de/zero-2-0),
    https://www.opengeodata.nrw.de

Requirements: ArcGIS Pro 3.x with Spatial Analyst and 3D Analyst.
Run from the ArcGIS Pro Python window or with propy.bat.
"""

import os
import arcpy
from arcpy.sa import (Raster, Con, IsNull, SetNull, SurfaceParameters,
                      Reclassify, RemapRange, DistanceAccumulation)

# --------------------------------------------------------------------------
# 0. Paths and settings
# --------------------------------------------------------------------------
COURSE_GDB = r"C:\path\to\uebung_04_kabeltrasse.gdb"   # course input data
WORK_GDB = r"C:\path\to\tue04_kabeltrasse.gdb"         # results

arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")
arcpy.env.overwriteOutput = True
arcpy.env.workspace = WORK_GDB
arcpy.env.scratchWorkspace = WORK_GDB

def course(name):
    """Full path of a dataset in the course geodatabase."""
    return os.path.join(COURSE_GDB, name)

# --------------------------------------------------------------------------
# 1. DTM: one reprojection to EPSG:25832, bilinear, 2 m, even-metre grid
# --------------------------------------------------------------------------
# The DTM comes in a custom projection equivalent to EPSG:4647 (UTM 32N with the
# zone number in the easting); the vector data are in EPSG:25832. Reprojecting
# once also applies the 2 m cell size allowed by the task, with bilinear
# resampling (appropriate for elevations) and cell corners on multiples of 2 m.
arcpy.management.ProjectRaster(
    in_raster=course("DGM2"),
    out_raster="DGM_25832_2m",
    out_coor_system=arcpy.SpatialReference(25832),
    resampling_type="BILINEAR",
    cell_size="2 2",
    Registration_Point="0 0",
)
DGM = os.path.join(WORK_GDB, "DGM_25832_2m")

# From here on, every raster shares the DTM grid (course standard: set the
# environments before any raster analysis).
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(25832)
arcpy.env.extent = arcpy.Describe(DGM).extent
arcpy.env.snapRaster = DGM
arcpy.env.cellSize = DGM
arcpy.env.mask = DGM

# --------------------------------------------------------------------------
# 2. Slope cost (€/m)
# --------------------------------------------------------------------------
slope = SurfaceParameters(
    in_raster=DGM,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    neighborhood_distance="2 Meters",          # = one cell, i.e. a 3 x 3 window
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit="METER",
    output_slope_measurement="DEGREE",
)
slope.save("neigung")

# Course classes: 0-3° -> 3, 3-7° -> 4, 7-15° -> 7, 15-30° -> 15, > 30° -> 50 €/m.
# (In the GUI run the last class ended at the raster maximum, 60.53°;
#  90° gives the identical result and holds for any input.)
slope_cost = Reclassify(
    "neigung", "VALUE",
    RemapRange([[0, 3, 3], [3, 7, 4], [7, 15, 7], [15, 30, 15], [30, 90, 50]]),
    "DATA",
)
slope_cost.save("k_neigung")

# --------------------------------------------------------------------------
# 3. Land-use surcharges and barriers
# --------------------------------------------------------------------------
SURCHARGES = {                                        # €/m added where present
    "layer_43002_AX_Wald_polygon": 100,               # woodland
    "layer_43003_AX_Gehoelz_polygon": 100,            # scrub
    "layer_42006_AX_Weg_polygon": 500,                # paths
    "layer_42001_AX_Strassenverkehr_polygon": 1500,   # roads
    "Altlasten": 2000,                                # contaminated sites
    "layer_44001_AX_Fliessgewaesser_polygon": 2500,   # watercourses
}
BARRIERS = [                                          # no route possible
    "layer_31001_AX_Gebaeude_polygon",                # buildings
    "layer_44006_AX_StehendesGewaesser_polygon",      # standing water
    "layer_43005_AX_Moor",                            # bog
]

# Rasterise every layer on the DTM grid (in the GUI: one batch run).
# The value (OBJECTID) does not matter: only "inside or outside" is used.
for fc in list(SURCHARGES) + BARRIERS:
    arcpy.conversion.PolygonToRaster(
        in_features=course(fc),
        value_field="OBJECTID",
        out_rasterdataset=f"r_{fc}",
        cell_assignment="CELL_CENTER",
        priority_field="NONE",
        cellsize=DGM,
    )

# --------------------------------------------------------------------------
# 4. Total cost surface (additive) with barriers as NoData
# --------------------------------------------------------------------------
# Con(IsNull(r), 0, eur): outside a polygon counts as 0 instead of turning the
# whole sum into NoData. SetNull(...) then makes the barrier cells NoData,
# which Distance Accumulation treats as impassable.
# (GUI run: one Raster Calculator expression with exactly this logic.)
cost = Raster("k_neigung")
for fc, eur in SURCHARGES.items():
    cost = cost + Con(IsNull(Raster(f"r_{fc}")), 0, eur)

barrier = None
for fc in BARRIERS:
    inside = ~IsNull(Raster(f"r_{fc}"))
    barrier = inside if barrier is None else (barrier | inside)

total_cost = SetNull(barrier, cost)
total_cost.save("k_gesamt")

# --------------------------------------------------------------------------
# 5. Accumulated cost from the wind farm and optimal paths
# --------------------------------------------------------------------------
acc = DistanceAccumulation(
    in_source_data=course("Transformator_Windpark"),
    in_cost_raster="k_gesamt",
    out_back_direction_raster="rueck_wp",
    distance_method="GEODESIC",
)
acc.save("akk_wp")

# "EACH_CELL": one route to every connection point, not only the cheapest,
# so the three variants can be compared (each line carries its PathCost).
arcpy.sa.OptimalPathAsLine(
    in_destination_data=course("Transformator"),
    in_distance_accumulation_raster="akk_wp",
    in_back_direction_raster="rueck_wp",
    out_polyline_features="trassen",
    destination_field="OBJECTID",
    path_type="EACH_CELL",
    create_network_paths="DESTINATIONS_TO_SOURCES",
)

# Readable fields for the variant table (OBJECTID 5 = North, 4 = South, 3 = East)
arcpy.management.AddFields("trassen", [
    ["route", "TEXT", "Connection point", 20],
    ["length_km", "DOUBLE", "Length (km)"],
    ["cost_eur", "LONG", "Cost (€)"],
    ["eur_per_m", "DOUBLE", "Average cost (€/m)"],
])
arcpy.management.CalculateFields("trassen", "ARCADE", [
    ["route", 'When($feature.DestID == 5, "North", $feature.DestID == 4, "South", '
              '$feature.DestID == 3, "East", "")'],
    ["length_km", "Round($feature.Shape_Length / 1000, 2)"],
    ["cost_eur", "Round($feature.PathCost, 0)"],
    ["eur_per_m", "Round($feature.PathCost / $feature.Shape_Length, 1)"],
])

# --------------------------------------------------------------------------
# 6. Parcels crossed by the cheapest route (North)
# --------------------------------------------------------------------------
arcpy.management.MakeFeatureLayer("trassen", "route_north", "DestID = 5")
arcpy.management.MakeFeatureLayer(course("layer_11001_AX_Flurstueck_polygon"),
                                  "parcels")
arcpy.management.SelectLayerByLocation("parcels", "INTERSECT", "route_north")
arcpy.conversion.ExportFeatures("parcels", "flst_trasse")

n_parcels = int(arcpy.management.GetCount("flst_trasse")[0])
official = sum(row[0] for row in arcpy.da.SearchCursor("flst_trasse", ["amt_fl"]))
geometric = sum(row[0] for row in arcpy.da.SearchCursor("flst_trasse", ["SHAPE@AREA"]))

print("Routes:")
with arcpy.da.SearchCursor("trassen", ["route", "length_km", "cost_eur", "eur_per_m"]) as rows:
    for route, km, eur, eur_m in rows:
        print(f"  {route:<6} {km:5.2f} km  €{eur:>7,}  €{eur_m}/m")
print(f"Parcels crossed by the North route: {n_parcels}")
print(f"  official area (amt_fl): {official:,.0f} m²")
print(f"  geometric area:         {geometric:,.0f} m²")

# --------------------------------------------------------------------------
# 7. Map preparation (layout only, no effect on the analysis)
# --------------------------------------------------------------------------
arcpy.ddd.RasterDomain(DGM, "study_area", "POLYGON")
arcpy.management.Merge([course("layer_43002_AX_Wald_polygon"),
                        course("layer_43003_AX_Gehoelz_polygon")], "woodland")
arcpy.management.Merge([course(fc) for fc in BARRIERS], "no_go")
