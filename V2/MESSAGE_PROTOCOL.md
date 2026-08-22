<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Alphabets V2 message protocol

## Purpose

This protocol carries text from an application to the Alphabets controller. The
controller lays out the text, converts characters to drum positions, and sends
the resulting targets to the modules through the
[`PROTOCOL.md`](PROTOCOL.md) module protocol.

```text
Application -> message protocol -> controller -> module protocol -> modules
                 UTF-8 JSON          layout       position bytes
```

The controller is the authority for the display geometry and installed
character set. Applications send text and presentation preferences; they do not
send `rows`, `columns`, or physical module addresses with each message.

## Display configuration

The controller stores these values as persistent installation settings:

| Setting | Meaning |
| --- | --- |
| `rows` | Number of physical character rows |
| `columns` | Number of characters in every row |
| `cell_to_module` | Physical module index for every logical display cell |
| `character_set` | The 64-position profile installed on every drum |
| `module_protocol` | Installed chain profile: `attiny1624-v2` or `attiny44-v1` |
| `layout_revision` | Monotonic revision changed with any setting above |

Logical cells use row-major order, starting at the upper-left corner. Cell
`(row, column)` has logical index `row * columns + column`, with both coordinates
starting at zero.

`cell_to_module` contains exactly `rows * columns` entries and is a permutation
of the physical module indexes `0` through `rows * columns - 1`. This permits a
straight, serpentine, or custom harness without exposing physical wiring to
applications. `rows * columns` is between 1 and 255, matching the module
protocol's discovery limit.

For a two-row, four-column display wired in a serpentine chain:

```text
Logical cells:       Physical module indexes:
0  1  2  3           0  1  2  3
4  5  6  7           7  6  5  4

cell_to_module = [0, 1, 2, 3, 7, 6, 5, 4]
```

The controller accepts display messages only when the discovered module count
equals `rows * columns` and the return path is healthy.

## Transport and packet envelope

Packets are UTF-8 JSON objects delimited by LF (`0x0A`). A packet occupies one
line on the transport; line breaks inside `text` are JSON `\n` escape sequences.
The examples below are pretty-printed only for readability. A packet is at most
4096 UTF-8 bytes including its final LF; `text` is at most 1024 Unicode
characters.

Every packet contains:

| Field | Type | Meaning |
| --- | --- | --- |
| `v` | integer | Protocol version; this document defines version `1` |
| `id` | string | Application-generated correlation ID, 1 to 64 characters |
| `type` | string | Packet type |

The same packet format can be carried over a USB serial stream or a TCP stream.
Transport selection does not change message semantics.

The machine-readable packet definitions are in
[`Code/message_protocol.schema.json`](Code/message_protocol.schema.json).

## Read the board capabilities

An application sends `display.describe` when it connects and whenever it wants
to refresh its preview constraints:

```json
{
  "v": 1,
  "id": "request-1",
  "type": "display.describe"
}
```

The controller responds with `display.description`:

```json
{
  "v": 1,
  "id": "request-1",
  "type": "display.description",
  "display": {
    "rows": 2,
    "columns": 8,
    "cells": 16,
    "layout_revision": 3
  },
  "modules": {
    "discovered": 16,
    "state": "ready"
  },
  "character_set": {
    "id": "international-64",
    "characters": " ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞÑÇÉÅÆØŁ0123456789.,:!?¡¿-/'&@%€$°"
  }
}
```

`state` is `ready`, `topology_fault`, or `return_path_fault`. The application
uses `rows`, `columns`, and `characters` for capacity checks and preview. The
controller applies the full configured normalization and alias rules when the
message arrives and remains the source of truth.

## Show text

An application sends `display.show`:

```json
{
  "v": 1,
  "id": "message-42",
  "type": "display.show",
  "text": "CAFÉ\nBERLIN",
  "layout_revision": 3,
  "layout": {
    "wrap": "word",
    "horizontal": "center",
    "vertical": "middle"
  }
}
```

Only `v`, `id`, `type`, and `text` are required. The optional
`layout_revision` makes a preview-safe request: when present, it must equal the
controller's current revision. The `layout` object accepts:

| Field | Values | Default |
| --- | --- | --- |
| `wrap` | `word`, `character`, `none` | `word` |
| `horizontal` | `left`, `center`, `right` | `center` |
| `vertical` | `top`, `middle`, `bottom` | `middle` |

The controller lays out a message deterministically:

1. Convert CRLF or CR line endings to LF and treat each LF as a forced row
   break. A trailing LF therefore creates an empty final line.
2. Normalize each non-LF segment to Unicode NFC and apply the selected
   character-set rules.
3. Wrap each paragraph to `columns` cells. `word` uses the last available ASCII
   space, removes that separator at the wrap, and splits at the cell boundary
   when a word is wider than a row. `character` wraps at every cell boundary.
   `none` reports `text_overflow` when any forced line is wider than a row.
4. Treat empty `text` as one empty logical line.
5. Reject the message when the resulting line count is greater than `rows`.
6. Apply horizontal and vertical alignment, filling every unused cell with the
   character set's blank position. When centering leaves an odd spare cell or
   row, the extra blank is placed on the right or bottom.
7. Convert the row-major cells through `cell_to_module`, encode the selected
   drum positions, and execute the module update.

Unsupported characters and overflow are explicit errors. The controller never
silently truncates text.

An empty `text` value clears the display because every cell is filled with the
blank position.

## Acceptance and completion

After validating and rendering the message, the controller responds with
`display.accepted`. `rendered` contains exactly `rows` strings, and every string
contains exactly `columns` display characters:

```json
{
  "v": 1,
  "id": "message-42",
  "type": "display.accepted",
  "layout_revision": 3,
  "rendered": [
    "  CAFÉ  ",
    " BERLIN "
  ]
}
```

Acceptance means that validation passed and movement started. When every module
reports the requested position and `ready = 1`, the controller emits:

```json
{
  "v": 1,
  "id": "message-42",
  "type": "display.ready"
}
```

The displayed message remains in place until the next `display.show`. Message
moderation, queue order, and display duration belong to the sending application.
The controller accepts one active update at a time and reports `busy` until it
has emitted `display.ready` for that update.

## Errors

The controller reports errors with the request's `id` whenever it can parse the
envelope:

```json
{
  "v": 1,
  "id": "message-42",
  "type": "display.error",
  "code": "text_overflow",
  "message": "Message needs 3 rows; the display has 2"
}
```

Version 1 defines these error codes:

| Code | Meaning |
| --- | --- |
| `invalid_packet` | JSON or required fields are invalid |
| `unsupported_version` | `v` is not supported |
| `invalid_character` | Text cannot be represented by the installed drums |
| `text_overflow` | Rendered text needs more configured rows |
| `stale_layout` | `layout_revision` does not match current settings |
| `topology_fault` | Discovered module count does not match display geometry |
| `return_path_fault` | Module-chain discovery did not complete |
| `busy` | A previously accepted update is still moving |
| `motion_timeout` | At least one module did not reach its requested position |

The application may refresh `display.describe` after `stale_layout`,
`topology_fault`, or `return_path_fault`. A motion timeout includes the logical
cell indexes affected in an optional `details.cells` array.

## Controller boundary

The two protocols meet inside the controller:

1. The message protocol produces a complete logical grid.
2. `cell_to_module` converts logical cells to physical chain positions.
3. The character-set profile converts characters to positions `0..63`.
4. The module protocol converts positions to commands `0x01..0x40` and sends
   them in reverse physical order.
5. Returned module statuses are mapped back to logical cells before an error is
   reported to the application.

This boundary keeps every module independent of text, rows, columns, Unicode,
alignment, and wiring layout. Modules only execute position commands.
