import os
from .base import BaseTrack


class LocalTrack(BaseTrack):
    def __init__(self, filepath, member) -> None:
        title = os.path.splitext(os.path.basename(filepath))[0]
        super().__init__(None, filepath, title, None, None, None, None, member)