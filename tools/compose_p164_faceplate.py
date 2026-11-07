#!/usr/bin/env python3
"""P164: compose ONE approved 1000x640 PCB header from existing P160 assets.

Not an image generator. No new typography, no visual redesign, no geometry
changes to the real controls. The LCD frame, chip, gold logo and all four outer
corner screws become a single static photograph. All LCD text stays VSTGUI.
"""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFilter

FILENAME = "125A_P164_PCB_Single_Header_1000x640.png"


def compose(resource: Path) -> Path:
    board = Image.open(resource / "125A_P160_PCB_1000x640.png").convert("RGBA")
    lcd = Image.open(resource / "125A_P160_Lcd_Complete_512x147.png").convert("RGBA")
    logo = Image.open(resource / "125A_AWE_Gold_Logo_236x147.png").convert("RGBA")
    assert board.size == (1000, 640), "Never distort the original PCB proportions"
    assert lcd.size == (512, 147)
    assert logo.size == (236, 147)
    before = board.copy()

    def patch(target, donor, blur):
        # Copy only ACTUAL photographed PCB substrate. The source P160 photo
        # has a thin residual old bezel at the far right and a crystal arc
        # hidden behind the live faceplate. Never inpaint with fabricated parts.
        x0, y0, x1, y1 = target
        w, h = x1 - x0, y1 - y0
        donor_im = board.crop(donor).resize((w, h), Image.Resampling.LANCZOS)
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle((2, 2, w-3, h-3),
                            radius=min(12, w//4), fill=255)
        board.paste(donor_im, (x0, y0),
                    mask.filter(ImageFilter.GaussianBlur(blur)))

    # Only two PCB substrate keepout strips, entirely within the LCD/chip bay.
    patch((248, 10, 337, 28), (336, 82, 425, 100), 4)
    patch((776, 26, 818, 216), (690, 34, 732, 224), 6)

    # IMPORTANT: P160 already carries the exact EMU8000 chip and its pin art.
    # Do not paste the original chip cutout again: its first 28 px accidentally
    # included the old LCD's right screw. That was the visible ghost screw.
    board.alpha_composite(logo.resize((193, 120), Image.Resampling.LANCZOS),
                          (39, 28))
    board.alpha_composite(lcd, (264, 16))  # just ONE complete LCD bezel

    # All outer hardware screws and the complete ISA connector survive byte
    # for byte because no retouch touches those regions.
    for x0, y0, x1, y1 in ((0,0,55,55),(945,0,1000,55),
                           (0,583,55,640),(945,583,1000,640)):
        assert board.crop((x0,y0,x1,y1)).tobytes() == (
            before.crop((x0,y0,x1,y1)).tobytes()), (
            "PCB exterior screw was modified")

    output = resource / FILENAME
    board.convert("RGB").save(output, optimize=True)
    assert Image.open(output).size == (1000,640)
    print("P164 single-header PCB ready:", output)
    return output


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: compose_p164_faceplate.py <resource-folder>")
    compose(Path(sys.argv[1]))
