"""Configuration: where the data comes from and where it lands.

Everything that could reasonably change lives here, so the other modules
stay about logic rather than about URLs.
"""
from pathlib import Path

# Mesa County Assessor tax parcels (layer 1 of the ParcelPointQuery service).
# Layer 0 is E911 address points, layer 2 is parcel centroids.
SERVICE_URL = (
    "https://mcgis.mesacounty.us/arcgis/rest/services"
    "/maps/ParcelPointQuery/MapServer/1"
)

# Only the fields the pipeline actually uses. The full table is ~75 columns;
# naming them explicitly keeps the payload small and makes the pull
# self-documenting -- you can see what the analysis depends on.
FIELDS = [
    "OBJECTID", "ACCOUNTNO", "PARCELNUM",

    # --- situs: where the property IS -------------------------------------
    # The county already stores this split into components, so this side
    # needs no parsing. LOCATION is the assembled line, used as a fallback.
    "LOCATION", "STRNUMBER", "STRDIR", "STRNAME", "STRMODE", "STRUNIT",
    "SITUS_CITY", "SITUS_STATE", "SITUS_ZIP",

    # --- mailing: where the tax BILL goes ---------------------------------
    # Free text. This is the side that needs normalizing.
    "MAILING", "MAILING_CITY", "MAILING_ST", "MAILING_ZIP",

    # --- context for downstream analysis ----------------------------------
    "OWNER", "PROPTYPE", "LNDUSE", "BLDGUSE", "TOTNOUNITS",
    "NBHD", "NBDESC", "SDATE", "TOTVALCUR", "Acres",
]

# Layer 2 of the same service: one point per parcel, and -- usefully -- it
# carries LATITUDE / LONGITUDE / UTM12_X / UTM12_Y as ordinary attribute
# fields, so location needs no geometry parsing and no reprojection.
POINTS_URL = (
    "https://mcgis.mesacounty.us/arcgis/rest/services"
    "/maps/ParcelPointQuery/MapServer/2"
)

POINT_FIELDS = [
    "ACCOUNTNO", "PARCEL_NUM",
    "LATITUDE", "LONGITUDE",   # WGS84, for anything that wants degrees
    "UTM12_X", "UTM12_Y",      # metres, for anything that wants distance
]

WHERE = "1=1"           # override on the command line with --where
PAGE_SIZE = 1000        # ArcGIS maxRecordCount is typically 1000-2000
ORDER_BY = "OBJECTID"   # REQUIRED: offset paging is only stable if sorted

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
RAW_DIR = CACHE_DIR / "raw"
POINTS_DIR = CACHE_DIR / "points"
OUT_DIR = ROOT / "out"

# Situs values are Mesa County; anything else in the mailing column is
# out-of-area by definition.
HOME_STATE = "CO"
