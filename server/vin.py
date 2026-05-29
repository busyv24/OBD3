# ════════════════════════════════════════
#  vin.py — VIN decoding via the NHTSA API
#
#  The NHTSA (National Highway Traffic Safety Administration) provides
#  a free API to decode Vehicle Identification Numbers. This module
#  wraps that API call and returns structured vehicle info.
#
#  API docs: https://vpic.nhtsa.dot.gov/api/
# ════════════════════════════════════════

import requests


def decode_vin(vin: str) -> dict:
    """Decode a VIN using the free NHTSA API.

    Args:
        vin: A 17-character Vehicle Identification Number.

    Returns:
        Dict with keys: make, model, year, trim, engine.
        On failure, returns "Unknown" values with an error key.
    """
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
        r = requests.get(url, timeout=5)
        data = r.json().get("Results", [])
        fields = {item["Variable"]: item["Value"] for item in data}
        return {
            "make":  fields.get("Make", "Unknown"),
            "model": fields.get("Model", "Unknown"),
            "year":  fields.get("Model Year", "Unknown"),
            "trim":  fields.get("Trim", ""),
            "engine": fields.get("Displacement (L)", ""),
        }
    except Exception as e:
        return {
            "make": "Unknown",
            "model": "Unknown",
            "year": "Unknown",
            "trim": "",
            "engine": "",
            "error": str(e),
        }
