class Duration:
    def __init__(self, seconds: int):
        self._seconds: int = int(seconds)

    @classmethod
    def from_text(cls, text: str):
        hms = text.split(":")
        result = 0
        for i, s in enumerate(hms[::-1]):
            result += int(s) * (60 ** i)
        return cls(result)
    
    @property
    def seconds(self):
        return self._seconds
    
    def __str__(self):
        h = self._seconds // 3600
        m = (self._seconds - h * 3600) // 60
        s = self._seconds % 60
        if h:
            result = f"{h}:{str(m).zfill(2)}:{str(s).zfill(2)}"
        else:
            result = f"{m}:{str(s).zfill(2)}"
        return result
    
    def __add__(self, other):
        return self.__class__(self.seconds + other.seconds)