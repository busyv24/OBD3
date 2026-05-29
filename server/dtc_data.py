# ════════════════════════════════════════
#  dtc_data.py — DTC codes, part mappings, and repair info
#
#  Pure data — no logic, no imports, no side effects.
#  This file is the single source of truth for:
#  - Which DTC codes map to which car parts
#  - Severity levels for each code
#  - Estimated repair costs, DIY feasibility, and time
# ════════════════════════════════════════

# Maps OBD2 diagnostic trouble codes to the affected part and severity.
# "part" must match the mesh names used in the 3D model / PARTS_DEF in scene.js.
DTC_TO_PART: dict[str, dict] = {
    "P0130": {"part": "O2_Sensor_Front",      "label": "O2 Sensor (Front)",          "severity": "high"},
    "P0131": {"part": "O2_Sensor_Front",      "label": "O2 Sensor (Front)",          "severity": "high"},
    "P0136": {"part": "O2_Sensor_Rear",       "label": "O2 Sensor (Rear)",           "severity": "medium"},
    "P0100": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "high"},
    "P0101": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "high"},
    "P0102": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "medium"},
    "P0120": {"part": "Throttle_Body",        "label": "Throttle Body",              "severity": "high"},
    "P0121": {"part": "Throttle_Body",        "label": "Throttle Body",              "severity": "medium"},
    "P0420": {"part": "Catalytic_Converter",  "label": "Catalytic Converter",        "severity": "medium"},
    "P0430": {"part": "Catalytic_Converter",  "label": "Catalytic Converter",        "severity": "medium"},
    "P0115": {"part": "Coolant_Temp_Sensor",  "label": "Coolant Temp Sensor",        "severity": "medium"},
    "P0116": {"part": "Coolant_Temp_Sensor",  "label": "Coolant Temp Sensor",        "severity": "low"},
    "P0335": {"part": "Crankshaft_Sensor",    "label": "Crankshaft Position Sensor", "severity": "critical"},
    "P0336": {"part": "Crankshaft_Sensor",    "label": "Crankshaft Position Sensor", "severity": "critical"},
    "P0400": {"part": "EGR_Valve",            "label": "EGR Valve",                  "severity": "low"},
    "P0401": {"part": "EGR_Valve",            "label": "EGR Valve",                  "severity": "medium"},
    "P0300": {"part": "Engine_Block",         "label": "Engine (Misfire Detected)",  "severity": "critical"},
    "P0301": {"part": "Engine_Block",         "label": "Cylinder 1 Misfire",         "severity": "critical"},
    "P0171": {"part": "Fuel_Injector",        "label": "Fuel Injector (Lean)",       "severity": "medium"},
    "P0172": {"part": "Fuel_Injector",        "label": "Fuel Injector (Rich)",       "severity": "medium"},
    "P0340": {"part": "Camshaft_Sensor",      "label": "Camshaft Position Sensor",   "severity": "high"},
    "P0011": {"part": "Camshaft_Sensor",      "label": "Camshaft Timing",            "severity": "high"},
}

# Repair estimates for each part. Used by the frontend to show cost/time info.
REPAIR_INFO: dict[str, dict] = {
    "O2_Sensor_Front":      {"cost": "$150-$300",  "diy": True,   "time": "1-2 hrs"},
    "O2_Sensor_Rear":       {"cost": "$120-$250",  "diy": True,   "time": "1 hr"},
    "MAF_Sensor":           {"cost": "$200-$400",  "diy": True,   "time": "30 min"},
    "Throttle_Body":        {"cost": "$300-$600",  "diy": False,  "time": "2-3 hrs"},
    "Catalytic_Converter":  {"cost": "$800-$2000", "diy": False,  "time": "2-4 hrs"},
    "Coolant_Temp_Sensor":  {"cost": "$50-$150",   "diy": True,   "time": "30 min"},
    "Crankshaft_Sensor":    {"cost": "$150-$300",  "diy": False,  "time": "1-3 hrs"},
    "EGR_Valve":            {"cost": "$200-$500",  "diy": False,  "time": "2 hrs"},
    "Engine_Block":         {"cost": "$500-$5000", "diy": False,  "time": "Shop visit"},
    "Fuel_Injector":        {"cost": "$150-$400",  "diy": False,  "time": "2 hrs"},
    "Camshaft_Sensor":      {"cost": "$100-$250",  "diy": True,   "time": "1 hr"},
}
