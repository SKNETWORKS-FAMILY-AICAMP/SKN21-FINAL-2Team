from dataclasses import dataclass, asdict
import json

@dataclass
class PlaceInfo:
    """ Executor 노드에서 구성한 장소 정보 """
    contenttypeid: str
    name: str
    address: str
    image_path: str
    map_url: str
    longitude: float
    latitude: float
    
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

