"""Import indirection to avoid circular app imports between conflicts and parcels."""
from apps.parcels.models import Parcel, Building, Road, Utility  # noqa: F401
