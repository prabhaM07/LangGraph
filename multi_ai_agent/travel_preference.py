from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Boolean

class TravelPreference(BaseModel):

    budget_max: Optional[int] = Field(
        default=None,
        description=(
            "Examples: 300, 1500. Return null if not specified."
        ),
        ge=0
    )

    activities: List[str] = Field(
        default_factory=list,
        description=(
            "Examples: ['beach', 'adventure', 'trekking', 'cultural', 'relaxation']. "
        )
    )

    travel_month: Optional[str] = Field(
        default=None,
        description=(
            "Examples: 'June', 'December', 'summer', 'winter'. "
        )
    )
    destination_state: List[str] = Field(
        default_factory=list,
        description=(
            "Examples: ['Tamil Nadu', 'west bengal', 'kerala', 'delhi']. "
        )
    )
    destination_country: List[str] = Field(
        default_factory=list,
        description=(
            "Examples: ['India', 'Asia', 'Europe', 'Bali']. "
        )
    )
    
    weather : bool = False




