from typing import TypedDict, Literal, Optional, List, Dict, Any

class State(TypedDict, total=False):
    user_input: str
    history: list
    
    # memory 요약
    memory_summary: str            # long-term memory 요약

    preferences: Dict[str, Any]           # 선호도 조사
    candidates: List[Dict[str, Any]]      # retrieval 결과

    # 최종
    answer: str
