import enum

class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class RoleType(str, enum.Enum):
    human = "human"
    ai = "ai"
