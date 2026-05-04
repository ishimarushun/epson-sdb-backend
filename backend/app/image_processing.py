import base64
import binascii
import io
import os
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError


DEFAULT_80MM_203DPI_WIDTH_DOTS = 576


@dataclass(frozen=True)
class EpsonRasterImage:
    width: int
    height: int
    data_base64: str


def prepare_image_for_80mm_203dpi(image_base64: str) -> EpsonRasterImage:
    raw = _decode_base64_image(image_base64)
    max_width = int(os.getenv("PRINTER_WIDTH_DOTS", str(DEFAULT_80MM_203DPI_WIDTH_DOTS)))

    try:
        with Image.open(io.BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source).convert("L")
    except UnidentifiedImageError as exc:
        raise ValueError("image_base64 must contain a valid image file") from exc

    if image.width > max_width:
        new_height = max(1, round(image.height * (max_width / image.width)))
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

    output_width = _round_up_to_multiple_of_8(image.width)
    if output_width != image.width:
        padded = Image.new("L", (output_width, image.height), 255)
        padded.paste(image, (0, 0))
        image = padded

    mono = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    raster = _pack_mono_image(mono)
    return EpsonRasterImage(
        width=mono.width,
        height=mono.height,
        data_base64=base64.b64encode(raster).decode("ascii"),
    )


def _decode_base64_image(image_base64: str) -> bytes:
    value = image_base64.strip()
    if "," in value and value.lower().startswith("data:"):
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image_base64 must be valid base64") from exc


def _round_up_to_multiple_of_8(value: int) -> int:
    return value if value % 8 == 0 else value + (8 - value % 8)


def _pack_mono_image(image: Image.Image) -> bytes:
    pixels = image.load()
    packed = bytearray()
    for y in range(image.height):
        for x_byte in range(0, image.width, 8):
            byte = 0
            for bit in range(8):
                x = x_byte + bit
                is_black = pixels[x, y] == 0
                if is_black:
                    byte |= 0x80 >> bit
            packed.append(byte)
    return bytes(packed)
