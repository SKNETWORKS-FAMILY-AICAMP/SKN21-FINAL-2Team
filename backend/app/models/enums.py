import enum

class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class RoleType(str, enum.Enum):
    human = "human"
    ai = "ai"

class LanguageType(str, enum.Enum):
    en = "en"
    ko = "ko"
    ja = "ja"
    zh = "zh"
