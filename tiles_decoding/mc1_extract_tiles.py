#!/usr/bin/python3

# Copyright 2014 LG
# License: GPLv3
"""
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Utility for the game "The Magic Candle 1", 1989 MS-DOS version (320x200, 16 colors).

  Extracts the images from an EGA Tile file (<game directory>/TILES/EGAxx.TIL).
  The tiles are displayed on the console & saved as PNG files (scaled x2
  for better readability on modern screens) The PNG files are saved in the
  tile directory.

USAGE:  ./mc1_extract_tiles.py <EGAxxx.TIL>   (the script must be executable)
        or python3 ./mc1_extract_tiles.py <EGAxxx.TIL>
Ex:     ./mc1_extract_tiles.py TILES/EGA17.TIL

Pb with the console output: the colors are limited (8 usually) & difficult to use.
If your console works fine, each color can have a normal & "bold" or brighter option.
If not, they will look bad on your screen. In that case, check the generated PNG...
=> If you don't know the intricaties of the Escape Codes, don't bother.
(The Console colors can only be approximated, only the PNG are correct.)
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
import sys
from mmap import ACCESS_READ, mmap
from PIL import Image, ImageDraw

"""
==========================================
The TIL file format
==========================================
0-0xFF: header
   The header is an array of 128 2-bytes blocks (BIG-endian),
   each of them contain the offset of the first byte of a tile.
   This means that each file contains a maximum of 128 tiles.
   If an offset is 0xffff, this means that the rest of
   the header is not used (all the next ones are 0xffff).

0x100-0x101: padding/separator

+ TILE block 0: 8*14 (pixels) + 2 (padding) => 114 bytes per tile
     0x00-0x07: line 1 (16 pixels!, 2 colors packed in each byte)
     ...
     0x62-0x69: line 14
     0x70-0x71: padding/separator
+ TILE block 1
   ...
   etc (N tiles)
   ...
+ TILE block N: last tile of the file
     0x00-0x07: line 1
     ...
     0x62-0x69: line 14
     0x70-0x71: padding/separator
0x??-EOF: some empty bytes (0x00) at the end, padding?, unknown usage
==========================================
"""

# Tiles are 16x14 pixels (but only use 8x14 bytes)
tile_packed_w = 8  # 8 bytes/line
tile_width = tile_packed_w * 2  # each byte of a line packs 2 pixels (1 pixel/nibble) => 16 pixels
tile_height = 14

scale_factor = 2  # we'll scale up the PNG images, the original 16x14 size is too small on a modern screen

group_hexa = ''  # stores Hex values of a tile (for console display)
group_esc_codes = ''  # stores Escape Codes (for Console display)
num_line = 0  # used to identify each tile line

# Match the Tile file value with the ASCII colors (for console display)
# & the EGA color for the generated tile files.
# Key: value read from the file (16 values corresponding to the EGA 16 colors mode)
#    => Values: console escape code, color name, (RGB value)
#       The console values appear _twice_ because their brightness is.
#       given as another parameter (not intuitive if you don't know this format)
#       Their colors are _approximated_ only!
#       See usage in the code below.
colors = {
    0x0: (30, "Black", (0, 0, 0)),
    0x1: (34, "Blue", (0, 0, 170)),
    0x2: (32, "Green", (0, 170, 0)),
    0x3: (36, "Cyan", (0, 170, 170)),
    0x4: (31, "Red", (170, 0, 0)),
    0x5: (35, "Magenta", (170, 0, 170)),
    0x6: (33, "Yellow", (170, 85, 0)),
    0x7: (37, "White/Light Grey", (170, 170, 170)),

    0x8: (30, "Dark Grey", (85, 85, 85)),
    0x9: (34, "Highlighted Blue", (85, 85, 255)),
    0xa: (32, "Highlighted Green", (85, 255, 85)),
    0xb: (36, "Highlighted Cyan", (85, 255, 255)),
    0xc: (31, "Highlighted Red", (255, 85, 85)),
    0xd: (35, "Highlighted Magenta", (255, 85, 255)),
    0xe: (33, "Highlighted yellow", (255, 255, 85)),
    0xf: (37, "White", (255, 255, 255))
}

tile_array = []  # stores a TILE (2 dimensional array)
line_array = []  # temp storage for one line/row of the Tile

skip = 0x102  # used to skip useless (?) bytes. Initialized to 0x102 to ignore the header

tiles_offset = []
tiles_offset_row = []
block = 0
tmp_val = 0
num_tile = 0  # we display each tile number before its extracted data
finished = False
offset = -2  # file offset (displayed in HEXadecimal on the console)


# Get the Escape color codes for displaying on the console
def get_esc_color_codes(pixel_color):
    if pixel_color in colors:
        # The unicode character "\u2588" is chosen because it's a big rectangle that looks reasonably good
        # on the console (ie the Tiles are recognizable)
        if pixel_color > 7:
            pixel = "\033[1;{0:02}m\u2588\033[1;m".format(colors[pixel_color][0])  # [1 => bright color
        else:
            pixel = "\033[0;{0:02}m\u2588\033[0;m".format(colors[pixel_color][0])  # [0 => normal color
    else:
        pixel = "?"  # should not happen!
    return pixel


print("=========== Displaying the HEADER table ===========")
# Get filename from prompt (we don't check for errors!)
filename = sys.argv[1]
with open(filename, "rb") as f:
    while True:
        byte = f.read(2)  # each pair of bytes gives a TILE offset
        offset += 2

        if not byte:
            break
        val = byte[0] + (byte[1] * 256)  # compute the tile offset

        if offset > 0xff:  # the header is always 256 (0xff) bytes long
            break

        if finished or ((block % 4 == 0) and (block > 0)):
            line_offset = hex(offset - 8)
            tiles_offset_row = map((lambda v: "{0:#06x}".format(v + 0xff + 3)), tiles_offset_row)
            group_hexa = ' '.join(tiles_offset_row)

            out = "{0:6}: {1}".format(line_offset, group_hexa)
            print(out)

            tiles_offset_row = []
            if finished:
                break

        if val == 0xFFFF:  # the next offset will all be 0xffff => no tiles
            finished = True
        else:
            tiles_offset_row.append(val)
            tiles_offset.append(val + 0xff + 3)  # '+0xff' = skip header, '+3' = skip 2 padding chars after header
            num_tile += 1
            block += 1

print("\n=========== Displaying the TILES ===========\n")

num_tile = -1  # number of tile (in sequence as read from the file)

# We load the whole file in memory, then we can access the bytes directly.
with open(filename, 'rb') as f, mmap(f.fileno(), 0, access=ACCESS_READ) as mm:
    for tile_start_offset in tiles_offset:
        num_tile += 1

        print("======= {0}/{1} ======= ".format(num_tile + 1, len(tiles_offset)))
        tile_pixels = []  # contains ONE tile
        tile_pixels_row = []  # unpacked
        pix_offset = 0

        #
        for d1 in range(tile_height):
            for d2 in range(tile_packed_w):
                val = mm[tile_start_offset + pix_offset]
                pix_offset += 1

                # One byte packs _2_ pixel values in the [0-15] range (we get them using a bit_mask)
                # (This packing is possible since the EGA mode only allows 16 colors...)
                pixel2_col = (val & 0x0f)
                pixel1_col = (val & 0xf0) >> 4  # >>4 to shift bits right => gives a [0-15] value

                tile_pixels_row.append(pixel1_col)
                tile_pixels_row.append(pixel2_col)

                group_esc_codes = ''.join(
                    (group_esc_codes, get_esc_color_codes(pixel1_col), get_esc_color_codes(pixel2_col)))

            tile_pixels.append(tile_pixels_row)

            hexa = map((lambda v: "{0:#04x}".format(v)), tile_pixels_row)
            group_hexa = ' '.join(hexa)  # stores the HEX values of the tile

            out = "{0:6}: {1}   {2} [{3}]".format(hex(tile_start_offset - tile_packed_w), group_hexa, group_esc_codes,
                                                  d1 + 1)
            print(out)
            tile_pixels_row = []
            group_hexa = ""
            group_esc_codes = ""

        # Generate a PNG of the tile
        im = Image.new("RGB", (tile_width, tile_height))
        draw = ImageDraw.Draw(im)
        for d1 in range(tile_height):
            for d2 in range(tile_width):
                px = tile_pixels[d1][d2]
                draw.point((d2, d1), fill=colors[px][2])
        del draw
        im2 = im.resize((tile_width * scale_factor, tile_height * scale_factor))  # the tile is scaled
        im2.save("{0}__{1:02}.png".format(filename, num_tile), "PNG")

        print()
