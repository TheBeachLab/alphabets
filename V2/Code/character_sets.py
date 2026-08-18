#!/usr/bin/env python3
"""Canonical 64-position character-set configuration for Alphabets V2."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import unicodedata
from typing import Any, Mapping, Sequence


CHARACTER_SET_PATH = Path(__file__).with_name("character_sets.json")


class CharacterSetError(ValueError):
    """Raised when a drum profile or message cannot be represented safely."""


@dataclass(frozen=True)
class CharacterSet:
    id: str
    name: str
    description: str
    characters: str
    uppercase_input: bool = False
    aliases: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        normalized = validate_characters(self.characters)
        object.__setattr__(self, "characters", normalized)
        aliases = dict(self.aliases or {})
        for source, target in aliases.items():
            if len(source) != 1:
                raise CharacterSetError(
                    f"alias source {source!r} in {self.id!r} must be one character"
                )
            if len(target) != 1 or target not in normalized:
                raise CharacterSetError(
                    f"alias target {target!r} in {self.id!r} is not on the drum"
                )
        object.__setattr__(self, "aliases", aliases)

    @property
    def positions(self) -> Mapping[str, int]:
        """Map every displayed character to its physical position (0..63)."""

        return {
            character: position for position, character in enumerate(self.characters)
        }

    def normalize_text(self, text: str) -> str:
        """Normalize user text to the exact glyphs printed on this drum."""

        normalized_text = unicodedata.normalize("NFC", text)
        output: list[str] = []
        aliases = self.aliases or {}

        for offset, source in enumerate(normalized_text):
            candidate = aliases.get(source, source)
            if candidate in self.positions:
                output.append(candidate)
                continue

            if self.uppercase_input:
                uppercase = source.upper()
                candidate = aliases.get(uppercase, uppercase)
                if len(candidate) == 1 and candidate in self.positions:
                    output.append(candidate)
                    continue

            raise CharacterSetError(
                f"character {source!r} at text offset {offset} is not supported "
                f"by {self.id!r}"
            )

        return "".join(output)

    def encode_positions(self, text: str) -> list[int]:
        """Encode text as physical drum positions (0..63)."""

        positions = self.positions
        return [positions[character] for character in self.normalize_text(text)]

    def encode_commands(self, text: str) -> list[int]:
        """Encode text as V2 move commands (0x01..0x40)."""

        return [position + 1 for position in self.encode_positions(text)]


def validate_characters(characters: str, positions: int = 64) -> str:
    """Return the NFC profile after validating a one-glyph-per-position drum."""

    if not isinstance(characters, str):
        raise CharacterSetError("characters must be a string")

    normalized = unicodedata.normalize("NFC", characters)
    if len(normalized) != positions:
        raise CharacterSetError(
            f"a drum requires exactly {positions} characters; got {len(normalized)}"
        )
    if len(set(normalized)) != positions:
        duplicates = sorted(
            {character for character in normalized if normalized.count(character) > 1}
        )
        raise CharacterSetError(
            f"every drum position must be unique; duplicate characters: {duplicates!r}"
        )
    if normalized.count(" ") != 1:
        raise CharacterSetError("a drum must contain exactly one ASCII space")

    for character in normalized:
        if character == " ":
            continue
        if not character.isprintable() or unicodedata.combining(character):
            raise CharacterSetError(
                f"drum character {character!r} must be one printable Unicode character"
            )

    return normalized


def load_catalog(path: Path = CHARACTER_SET_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        catalog = json.load(handle)

    if catalog.get("schema_version") != 1:
        raise CharacterSetError("unsupported character-set catalog schema")
    if catalog.get("positions") != 64:
        raise CharacterSetError("V2 character sets must contain 64 positions")
    return catalog


def load_presets(path: Path = CHARACTER_SET_PATH) -> dict[str, CharacterSet]:
    catalog = load_catalog(path)
    presets: dict[str, CharacterSet] = {}
    for data in catalog.get("presets", []):
        preset = CharacterSet(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            characters=data["characters"],
            uppercase_input=data.get("uppercase_input", False),
            aliases=data.get("aliases", {}),
        )
        if preset.id in presets:
            raise CharacterSetError(f"duplicate preset id: {preset.id!r}")
        presets[preset.id] = preset

    default_preset = catalog.get("default_preset")
    if default_preset not in presets:
        raise CharacterSetError(f"unknown default preset: {default_preset!r}")
    return presets


def resolve_character_set(
    settings: Mapping[str, Any], path: Path = CHARACTER_SET_PATH
) -> CharacterSet:
    """Resolve either a named preset or a custom 64-character settings value."""

    unexpected_settings = set(settings) - {"settings_version", "character_set"}
    if unexpected_settings:
        raise CharacterSetError(
            f"unknown settings keys: {sorted(unexpected_settings)!r}"
        )
    if settings.get("settings_version") != 1:
        raise CharacterSetError("settings_version must be 1")

    config = settings.get("character_set")
    if not isinstance(config, Mapping):
        raise CharacterSetError("settings.character_set must be an object")

    preset_id = config.get("preset")
    custom = config.get("custom")
    if (preset_id is None) == (custom is None):
        raise CharacterSetError(
            "settings.character_set must define exactly one of preset or custom"
        )

    if preset_id is not None:
        unexpected_config = set(config) - {"preset"}
        if unexpected_config:
            raise CharacterSetError(
                f"unknown preset settings: {sorted(unexpected_config)!r}"
            )
        if not isinstance(preset_id, str):
            raise CharacterSetError("settings.character_set.preset must be a string")
        presets = load_presets(path)
        try:
            return presets[preset_id]
        except KeyError as error:
            raise CharacterSetError(
                f"unknown character-set preset: {preset_id!r}"
            ) from error

    unexpected_config = set(config) - {
        "name",
        "custom",
        "uppercase_input",
        "aliases",
    }
    if unexpected_config:
        raise CharacterSetError(
            f"unknown custom settings: {sorted(unexpected_config)!r}"
        )
    if not isinstance(custom, str):
        raise CharacterSetError("settings.character_set.custom must be a string")

    name = config.get("name", "Custom 64")
    if not isinstance(name, str) or not name:
        raise CharacterSetError(
            "settings.character_set.name must be a non-empty string"
        )

    uppercase_input = config.get("uppercase_input", False)
    if not isinstance(uppercase_input, bool):
        raise CharacterSetError(
            "settings.character_set.uppercase_input must be a boolean"
        )

    aliases = config.get("aliases", {})
    if not isinstance(aliases, Mapping):
        raise CharacterSetError("settings.character_set.aliases must be an object")
    validated_aliases: dict[str, str] = {}
    for source, target in aliases.items():
        if not isinstance(source, str) or not isinstance(target, str):
            raise CharacterSetError("custom aliases must map strings to strings")
        validated_aliases[source] = target

    return CharacterSet(
        id="custom-64",
        name=name,
        description="User-defined 64-position drum profile.",
        characters=custom,
        uppercase_input=uppercase_input,
        aliases=validated_aliases,
    )


def _load_settings(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise CharacterSetError("settings root must be an object")
    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="list the installed presets")

    show = subparsers.add_parser("show", help="show one preset and its positions")
    show.add_argument("preset")

    validate = subparsers.add_parser("validate", help="validate a settings JSON file")
    validate.add_argument("settings", type=Path)

    encode = subparsers.add_parser(
        "encode", help="encode text using a settings JSON file"
    )
    encode.add_argument("settings", type=Path)
    encode.add_argument("text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        presets = load_presets()
        if args.command == "list":
            for preset in presets.values():
                print(f"{preset.id}\t{preset.name}\t{preset.characters}")
            return 0

        if args.command == "show":
            try:
                selected = presets[args.preset]
            except KeyError as error:
                raise CharacterSetError(f"unknown preset: {args.preset!r}") from error
            for position, character in enumerate(selected.characters):
                label = "SPACE" if character == " " else character
                print(f"{position:02d}\t0x{position + 1:02X}\t{label}")
            return 0

        selected = resolve_character_set(_load_settings(args.settings))
        if args.command == "validate":
            print(f"OK: {selected.id} has 64 unique positions")
            return 0

        normalized = selected.normalize_text(args.text)
        commands = selected.encode_commands(args.text)
        print(normalized)
        print(" ".join(f"0x{command:02X}" for command in commands))
        return 0
    except (CharacterSetError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
