from pathlib import Path
from typing import Tuple
from sys import stderr
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from matplotlib import font_manager

# Constants
DEFAULT_FONT = "Arial"
DEFAULT_FONT_SIZE = 100
DEFAULT_PADDING = 75


def perror(*args, **kwargs) -> None:
    print(*args, file=stderr, **kwargs)

def wrap_text(text: str, font: ImageFont, max_len: int) -> str:
    lines = [""]
    for word in text.split(' '):
        line = f"{lines[-1]} {word}".strip()
        if font.getlength(line) <= max_len:
            lines[-1] = line
        else:
            # If the word is still too long for a line, split it too
            if font.getlength(word) <= max_len:
                lines.append(word)
            else:
                word_part = ""
                for c in word:
                    word_part += c
                    if font.getlength(word_part) > max_len:
                        lines.append(word_part[:-1])
                        word_part = c
                if len(word_part) > 0:
                    lines.append(word_part)
    return "\n".join(lines)


def resize_preserve_ratio(img: Image, width: int, height: int, rgba: Tuple[int] = (0, 0, 0, 0)) -> Image:
    """
    Resize image, maintaining ratio and with a given background color.
    Offset is set to (centre, 0).
    Taken from https://stackoverflow.com/a/52969463
    """
    ratio_w = width / img.width
    ratio_h = height / img.height
    if ratio_w < ratio_h:
        # Fixed by width
        resized_width = width
        resized_height = round(ratio_w * img.height)
    else:
        # Fixed by height
        resized_width = round(ratio_h * img.width)
        resized_height = height

    img_resized = img.resize((resized_width, resized_height), Image.LANCZOS)
    bg = Image.new("RGBA", (width, height), rgba)
    offset = (round((width - resized_width)/2), 0)
    bg.paste(img_resized, offset)

    return bg.convert("RGB")


def add_caption(img_file: Path, cap_file: Path, out_file: Path, font_size: int, font_path: str, padding: int):
    try:
        img_orig = Image.open(img_file)
        font = ImageFont.truetype(font_path, font_size)
        text = cap_file.read_text(encoding='utf-8', errors="strict")
    except UnidentifiedImageError:
        perror(f"ERROR: Could not recognise the given file as an image: {img_file.resolve()}.")
        exit(1)
    except OSError:
        perror(f"ERROR: Your font is installed, but somehow the font file could not be opened. Font path: {font_path}")
        exit(1)
    except ValueError as e:
        perror(f"ERROR: Could not interpret the given text file as UTF-8. Please ensure the encoding of the text file is UTF-8. Full error: {str(e)}")
        exit(1)

    # Construct textbox
    wrapped_text = wrap_text(text, font, img_orig.width-padding)
    ## Obtain text height for multiline text
    draw = ImageDraw.Draw(img_orig)
    text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font)
    text_height = text_bbox[3] - text_bbox[1]

    # Resize with additional space
    resized_img = resize_preserve_ratio(img_orig, img_orig.width, img_orig.height + (padding * 2) + text_height)
    draw = ImageDraw.Draw(resized_img)
    draw.text((resized_img.width/2, img_orig.height + padding), wrapped_text, font=font, fill='White', anchor="ms")
    resized_img.save(out_file)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Adds Captions based on a text file.")
    parser.add_argument("imagefile", type=str, help="Image File")
    parser.add_argument("captionfile", type=str, help="Caption File")
    parser.add_argument("-o", "--out", type=str, help="Output File", default=None)
    parser.add_argument("-f", "--force", action="store_true", help="Overwrites output file if it already exists.")
    parser.add_argument("-S", "--size", type=int, help="Caption Size", default=DEFAULT_FONT_SIZE)
    parser.add_argument("-F", "--font", type=str, help="Caption Font", default=DEFAULT_FONT)
    parser.add_argument("-P", "--padding", type=int, help="Caption Padding", default=DEFAULT_PADDING)

    args = parser.parse_args()
    image_file = Path(args.imagefile)
    caption_file = Path(args.captionfile)
    out_file = image_file.parent.joinpath(image_file.stem + "_cap" + image_file.suffix)
    padding = args.padding
    if args.out is not None:
        out_file = Path(args.outfile)

    if not image_file.is_file():
        perror(f"ERROR: {image_file.resolve()} is not a file!")
        exit(1)
    if not caption_file.is_file():
        perror(f"ERROR: {caption_file.resolve()} is not a file!")
        exit(1)
    if out_file.is_file() and not args.force:
        perror(f"ERROR: {out_file.resolve()} already exists!")
        exit(1)

    try:
        font_filepath = font_manager.findfont(args.font, fallback_to_default=False)
    except ValueError:
        # Could not find the font
        print(f"WARNING: Could not find font \"{args.font}\", defaulting to {DEFAULT_FONT}.")
        font_filepath = font_manager.findfont(DEFAULT_FONT)

    add_caption(image_file, caption_file, out_file, args.size, font_filepath, padding)
    print(f"Created new image: {out_file.resolve()}")

