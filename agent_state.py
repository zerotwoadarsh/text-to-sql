from typing import TypedDict, Optional
import pandas as pd

class AgentState(TypedDict):
    question: str
    sql: Optional[str]
    error: Optional[str]
    data: Optional[pd.DataFrame]
    retry_count: int
    max_retries: int
    success: bool