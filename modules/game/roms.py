# Copyright (c) 2026 realgarit
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO

from modules.core.runtime import get_base_path

ROMS_DIRECTORY = get_base_path() / "roms"

from modules.util.rom_version import GBA_GAME_NAME_MAP, GBA_ROMS, GB_ROMS, ROMLanguage

CUSTOM_GBA_ROM_HASHES: set[str] | None = None


@dataclass
class ROM:
    file: Path
    game_name: str
    game_title: str
    game_code: str
    language: ROMLanguage
    maker_code: str
    revision: int

    @property
    def short_game_name(self) -> str:
        return self.game_name.replace("Pokémon ", "")

    @property
    def is_rse(self) -> bool:
        return self.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]

    @property
    def is_rs(self) -> bool:
        return self.game_title in ["POKEMON RUBY", "POKEMON SAPP"]

    @property
    def is_emerald(self) -> bool:
        return self.game_title == "POKEMON EMER"

    @property
    def is_ruby(self) -> bool:
        return self.game_title == "POKEMON RUBY"

    @property
    def is_sapphire(self) -> bool:
        return self.game_title == "POKEMON SAPP"

    @property
    def is_frlg(self) -> bool:
        return self.game_title in ["POKEMON FIRE", "POKEMON LEAF"]

    @property
    def is_fr(self) -> bool:
        return self.game_title == "POKEMON FIRE"

    @property
    def is_lg(self) -> bool:
        return self.game_title == "POKEMON LEAF"

    @property
    def is_crystal(self) -> bool:
        return self.game_title == "PM_CRYSTAL"

    @property
    def is_gold(self) -> bool:
        return self.game_title == "POKEMON_GLD"

    @property
    def is_silver(self) -> bool:
        return self.game_title == "POKEMON_SLV"

    @property
    def is_gs(self) -> bool:
        return self.is_gold or self.is_silver

    @property
    def is_gen3(self) -> bool:
        return self.is_rse or self.is_frlg

    @property
    def is_gen2(self) -> bool:
        return self.is_crystal or self.is_gs

    @property
    def id(self) -> str:
        return f"{self.game_code}{self.language.value}{self.revision}"


class InvalidROMError(Exception):
    pass


rom_cache: dict[str, ROM] = {}


def list_available_roms(force_recheck: bool = False) -> list[ROM]:
    """
    This scans all files in the `roms/` directory and returns any entry that might
    be a valid GB/GBA ROM, along with some metadata that could be extracted from the
    ROM header.

    The GBA ROM (header) structure is described on this website:
    https://problemkaputt.de/gbatek-gba-cartridge-header.htm

    And here is the same for GB(C) ROMs:
    https://gbdev.gg8.se/wiki/articles/The_Cartridge_Header

    :param force_recheck: Whether to ignore the cached ROM list that is generated
                          the first time this function is called. This might be a
                          bit slow if there are a lot of ROMs available; mostly
                          because of the expensive SHA1 hash of every file.
    :return: List of all the valid ROMS that have been found
    """
    global rom_cache

    if force_recheck:
        rom_cache.clear()

    if not ROMS_DIRECTORY.is_dir():
        raise RuntimeError(f"Directory {str(ROMS_DIRECTORY)} does not exist!")

    result = []
    for file in ROMS_DIRECTORY.iterdir():
        if file.is_file():
            try:
                rom = load_rom_data(file)
                if rom.is_gen3:
                    result.append(rom)
            except InvalidROMError:
                pass
    return result


def _load_gba_rom(file: Path, handle: BinaryIO) -> ROM:
    global CUSTOM_GBA_ROM_HASHES
    custom_gba_rom_hashes_file = get_base_path() / "profiles" / "extra_allowed_roms.txt"
    if CUSTOM_GBA_ROM_HASHES is None and custom_gba_rom_hashes_file.exists():
        CUSTOM_GBA_ROM_HASHES = set()
        with open(custom_gba_rom_hashes_file, "r") as custom_gba_rom_hashes_file_handle:
            for line in custom_gba_rom_hashes_file_handle.readlines():
                if line.strip() != "":
                    CUSTOM_GBA_ROM_HASHES.add(line.strip().lower())

    handle.seek(0x0)
    sha1 = hashlib.sha1()
    sha1.update(handle.read())
    is_unsupported = False
    if sha1.hexdigest() not in GBA_ROMS:
        if CUSTOM_GBA_ROM_HASHES is not None and (
            sha1.hexdigest() in CUSTOM_GBA_ROM_HASHES
            or file.name.lower() in CUSTOM_GBA_ROM_HASHES
            or "*" in CUSTOM_GBA_ROM_HASHES
        ):
            is_unsupported = True
        else:
            raise InvalidROMError("ROM not supported.")

    handle.seek(0xA0)
    game_title = handle.read(12).decode("ascii")
    game_code = handle.read(4).decode("ascii")
    maker_code = handle.read(2).decode("ascii")

    handle.seek(0xBC)
    revision = int.from_bytes(handle.read(1), byteorder="little")

    if game_title not in GBA_GAME_NAME_MAP:
        raise InvalidROMError(f"Unsupported game: {game_title}")
    else:
        game_name = GBA_GAME_NAME_MAP[game_title] if not is_unsupported else f"Unsupported {game_title[8:]}"

    game_name += f" ({game_code[3]})"
    if revision > 0:
        game_name += f" (Rev {revision})"

    return ROM(file, game_name, game_title, game_code[:3], ROMLanguage(game_code[3]), maker_code, revision)


def _load_gb_rom(file: Path, handle: BinaryIO) -> ROM:
    handle.seek(0x134)
    game_title = handle.read(11).rstrip(b"\x00").decode("ascii")
    maker_code = handle.read(4).decode("ascii")

    handle.seek(0x0)
    sha1 = hashlib.sha1()
    sha1.update(handle.read())
    rom_hash = sha1.hexdigest()
    if rom_hash not in GB_ROMS:
        raise InvalidROMError(f"{file.name}: ROM not supported. ('{game_title}')")

    game_name, revision, language = GB_ROMS[rom_hash]
    return ROM(file, f"{game_name} ({language.value})", game_title, "GBCR", language, maker_code, revision)


def load_rom_data(file: Path) -> ROM:
    # Prefer cached data, so we can skip the expensive stuff below
    global rom_cache
    if str(file) in rom_cache:
        return rom_cache[str(file)]

    # GBA cartridge headers are 0xC0 bytes long and GB(C) headers are even longer, so any
    # files smaller than that cannot be a ROM.
    if file.stat().st_size < 0xC0:
        raise InvalidROMError("This does not seem to be a valid ROM (file size too small.)")

    with open(file, "rb") as handle:
        # The byte at location 0xB2 must have value 0x96 in valid GBA ROMs
        handle.seek(0xB2)
        gba_magic_number = handle.read(1)
        if gba_magic_number == b"\x96":
            rom_cache[str(file)] = _load_gba_rom(file, handle)
            return rom_cache[str(file)]

        # GB(C) ROMs contain the Nintendo logo, which starts with 0xCEED6666
        handle.seek(0x104)
        gb_magic_string = handle.read(4)
        if gb_magic_string == b"\xce\xed\x66\x66":
            rom_cache[str(file)] = _load_gb_rom(file, handle)
            return rom_cache[str(file)]

    raise InvalidROMError(f"File `{file.name}` does not seem to be a valid ROM (magic number missing.)")
