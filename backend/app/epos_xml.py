import html
import os

from app.image_processing import EpsonRasterImage


def build_text_epos_xml(text: str, copies: int = 1) -> str:
    copies = max(1, copies)
    escaped = html.escape(text, quote=False)
    body = "".join(
        f"<text>{escaped}</text><feed line=\"3\" /><cut />"
        for _ in range(copies)
    )
    return (
        '<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">'
        f"{body}"
        "</epos-print>"
    )


def build_image_epos_xml(image: EpsonRasterImage, copies: int = 1) -> str:
    copies = max(1, copies)
    body = "".join(
        "<image "
        f"width=\"{image.width}\" "
        f"height=\"{image.height}\" "
        "color=\"color_1\" "
        "mode=\"mono\">"
        f"{image.data_base64}"
        "</image>"
        "<feed line=\"3\" />"
        "<cut />"
        for _ in range(copies)
    )
    return (
        '<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">'
        f"{body}"
        "</epos-print>"
    )


def build_composite_epos_xml(text: str, image: EpsonRasterImage | None, copies: int = 1) -> str:
    copies = max(1, copies)
    escaped = html.escape(text, quote=False)
    parts: list[str] = []
    for _ in range(copies):
        if image:
            parts.append(
                "<image "
                f"width=\"{image.width}\" "
                f"height=\"{image.height}\" "
                "color=\"color_1\" "
                "mode=\"mono\">"
                f"{image.data_base64}"
                "</image>"
                "<feed line=\"1\" />"
            )
        if escaped:
            parts.append(f"<text>{escaped}</text><feed line=\"3\" />")
        else:
            parts.append("<feed line=\"3\" />")
        parts.append("<cut />")
    return (
        '<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">'
        f"{''.join(parts)}"
        "</epos-print>"
    )


def wrap_sdp_print_request(epos_print_xml: str, device_id: str | None = None) -> str:
    devid = html.escape(device_id or os.getenv("DEFAULT_DEVICE_ID", "local_printer"), quote=False)
    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<PrintRequestInfo>"
        "<ePOSPrint>"
        "<Parameter>"
        f"<devid>{devid}</devid>"
        "<timeout>10000</timeout>"
        "</Parameter>"
        "<PrintData>"
        f"{epos_print_xml}"
        "</PrintData>"
        "</ePOSPrint>"
        "</PrintRequestInfo>"
    )
