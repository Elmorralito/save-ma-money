from enum import Enum


class RealStateAssetAccountsOwnership(Enum):

    FULL = "FULL"
    PARTIAL = "PARTIAL"


class RealStateAssetAccountsAreaUnits(Enum):

    SQ_MT = "SQ_MT"
    SQ_FT = "SQ_FT"
    ACRES = "ACRES"
    HECTARES = "HECTARES"
    BLOCKS = "BLOCKS"
