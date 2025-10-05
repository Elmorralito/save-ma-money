"""Enumeration module for the Papita Transactions system.

This module defines various enumeration types used throughout the Papita Transactions
system to represent fixed sets of values for different attributes of models.

Classes:
    RealEstateAssetAccountsOwnership: Enumeration for real estate ownership types.
    RealEstateAssetAccountsAreaUnits: Enumeration for area measurement units in real estate.
"""

from enum import Enum


class RealEstateAssetAccountsOwnership(Enum):
    """Enumeration for types of real estate ownership.

    This enumeration represents the different types of ownership that can be
    applied to real estate assets in the system.

    Attributes:
        FULL: Complete ownership of the property.
        PARTIAL: Partial ownership of the property, typically used for shared properties.
    """

    FULL = "FULL"
    PARTIAL = "PARTIAL"


class RealEstateAssetAccountsAreaUnits(Enum):
    """Enumeration for area measurement units used in real estate assets.

    This enumeration represents the different units of measurement that can be
    used to specify the area of real estate properties in the system.

    Attributes:
        SQ_MT: Square meters.
        SQ_FT: Square feet.
        AC: Acres.
        HA: Hectares.
        BLK: Blocks (typically used in urban planning).
    """

    SQ_MT = "SQ_MT"
    SQ_FT = "SQ_FT"
    AC = "AC"
    HA = "HA"
    BLK = "BLK"


class TypesClassifications(Enum):

    ASSETS = "ASSETS"
    LIABILITIES = "LIABILITIES"
    TRANSACTIONS = "TRANSACTIONS"
