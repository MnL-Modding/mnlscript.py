import dataclasses
import os
import struct
import typing
from typing import override

import mnllib.dt
import mnllib.n3ds


@dataclasses.dataclass(frozen=True)
class Sound:
    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return (self.bank, self.sound_id) == (other.bank, other.sound_id)
        return NotImplemented

    bank: int
    sound_id: int


def load_sound_names(
    sound_data: (
        typing.BinaryIO | str | os.PathLike[str]
    ) = mnllib.n3ds.fs_std_romfs_path(mnllib.dt.SOUND_DATA_PATH),
) -> dict[Sound, str]:
    with mnllib.stream_or_open_file(sound_data, "rb") as sound_data:
        sound_names: dict[Sound, str] = {}

        while True:
            bank_offset = sound_data.tell()
            data = sound_data.read(12)
            if data == b"":
                break
            bank_id, record_count, next_bank_offset = struct.unpack("<III", data)

            sound_data.seek(0x14 + record_count * 16, os.SEEK_CUR)
            for i in range(record_count):
                (length,) = struct.unpack("<B", sound_data.read(1))
                sound_names[Sound(bank_id, i)] = sound_data.read(length)[:-1].decode()

            sound_data.seek(bank_offset + next_bank_offset)

        return sound_names
