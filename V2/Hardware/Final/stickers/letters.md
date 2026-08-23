<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 character sets

Every V2 drum has exactly 64 physical positions. The controller stores the
selected character-set setting and translates user text into the matching
position commands. Modules only receive positions, so the selected software
sequence must match the physical flap order.

The canonical machine-readable definitions are in
[`character_sets.json`](character_sets.json). They are validated and consumed
through [`character_sets.py`](character_sets.py).

## Physical compatibility

The alphabet is not interchangeable independently of the physical hardware.
`demo-64` belongs to **V2 Prototipo** (55 mm cards) and `international-64`
belongs to **V2 Definitivo** (50 mm cards). Their matched sticker, card, drum
and enclosure contracts are in [`../../variants/`](../../variants/README.md).

Do not select a preset for a drum that was printed with the other sequence.
Likewise, a Custom 64 setting requires a separately manufactured set of
matched flaps; it is not a software-only conversion of either existing drum.

## International 64

`international-64` is the default preset. Position 0 is the blank flap, so a
homed display starts empty.

```text
 ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞÑÇÉÅÆØŁ0123456789.,:!?¡¿-/'&@%€$°
```

This sequence contains exactly 64 unique characters:

- one blank;
- `A` to `Z`;
- complete uppercase German: `Ä Ö Ü ẞ`;
- `Ñ Ç É Å Æ Ø Ł` for practical additional Latin-script coverage;
- `0` to `9`;
- `. , : ! ? ¡ ¿ - / ' & @ % € $ °`.

The German group follows the uppercase inventory in the
[2024 official German spelling rules, page 31](https://www.rechtschreibrat.com/DOX/RfdR_Amtliches-Regelwerk_2024.pdf):
`A–Z`, `Ä`, `Ö`, `Ü`, and `ẞ`.

The preset normalizes lowercase input to uppercase, preserves the characters
printed on the drum, and maps common unsupported Latin diacritics to an
available base letter. Unsupported characters cause an explicit error instead
of silently moving to the wrong flap.

## Demo 64

`demo-64` preserves the physical order of the original demo drums already
installed on ten modules. Its blank flap remains at position 63.

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZ:.0123456789$€&@%×/·#=*+-±()<>,'°■£~©␠
```

Here `␠` denotes the position-63 blank; the machine-readable value in the
catalog contains an ASCII space.

## Custom 64

A custom setting contains the exact physical order as one 64-character Unicode
string. Validation requires:

- exactly 64 printable characters after NFC normalization;
- 64 unique positions;
- exactly one ASCII space;
- one Unicode character per physical position.

Preset setting:

```json
{
  "settings_version": 1,
  "character_set": {
    "preset": "international-64"
  }
}
```

Custom setting:

```json
{
  "settings_version": 1,
  "character_set": {
    "name": "My 64",
    "custom": " ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞÑÇÉÅÆØŁ0123456789.,:!?¡¿-/'&@%€$°",
    "uppercase_input": true
  }
}
```

Validate a setting and test its position encoding:

```sh
python3 V2/Hardware/Final/stickers/character_sets.py validate V2/Hardware/Final/stickers/settings.example.json
python3 V2/Hardware/Final/stickers/character_sets.py encode V2/Hardware/Final/stickers/settings.example.json "Grüße, señor! 20°"
```
