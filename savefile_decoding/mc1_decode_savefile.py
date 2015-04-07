#!/usr/bin/python3
from mmap import ACCESS_READ, mmap
import operator
import argparse

"""
This script will decode a Magic Candle 1 save file.
License: GPLv3

USAGE:  python3 <script>  <save_file.MCS>

MC1 allows 8 different save files labelled xxxxx1.mcs to xxxxx8.mcs
where xxxxx is the name displayed when starting the game.
Ex: LUKAS1.MCS

Those files are encoded by a XOR function which also depends on the OFFSET.

The files -roughly- follow a 6 chars per blocks pattern: to analyse a file,
we split the file in 6 chars long lines. The 6 number is related to the
number of heroes (ex: the first 6 values of the file are the current STRENGTH 
attribute of your 6 heroes).

The complete description of the fields can be found in a joined ODF/PDF file.
Th description file shows the encoded -original- values followed by the decoded values in Hexa, in Decimal and as Characters and their interpretation.
(The description file example values have been generated with this script, using one of my save file as input).

To get a real (decoded) value from the save file you must apply the following formula (to each byte):

real_value = ( (offset of the save_file_value byte + 0xa5) & 0xFF ) XOR save_file_value

(The '& 0xFF' operation means that you only keep the last 2 digits, ex: 0xE50 & 0xFF => 0x50)

Example (see the joined ODF/PDF file for the full example):
0x1c8 , 0x23 0x21 0x21 0x35 0x71 0x3e : 0x4e 0x4f 0x4e 0x45 0x00 0x4c : 78 79 78 69 0 76 : NONE.L  => Heroes names (LUKAS, SAKAR, etc.)

To get the First letter of the heroe name, you take the value at the offset 0x1cd ( 0x1c8+5 ) ==> 0x3e (in Hexa).
real_value = ((0x1cd + 0xa5) & 0xFF) XOR 0x3e
real_value = ( 0x272 & 0xFF) XOR 0x3e
real_value = ( 0x72 ) XOR 0x3e
real_value = 0x4C
real_value = 76 (in decimal)
real_value = 'L', which is the letter L in uppercase (76th character in an ASCII table)
"""


def dcode(byte_offset, byte_value):
    """
    Decode (or encode, the method is the same) the byte value located at the offset.
    The offset is the byte number of the byte to decode/encode, starting from the beginning of the save-file.
    '0xA5' is a magic number used by the game for the operation.
    '& 0xFF' is used to keep only the byte value (prevents overflows)
    :param byte_offset: offset of the byte that we are encoding/decoding (starting from the beginning of the file)
    :param byte_value: encoding/decoding the byte located at the position 'offset' in the save-file
    """
    return operator.xor((byte_offset + 0xA5), byte_value) & 0xFF


parser = argparse.ArgumentParser(description='View the decoded save-file.')
parser.add_argument('savefile', nargs='?', help='Name of the savefile (xxxxx.MCS)')
parser.add_argument('--csv-friendly', action='store_true',
                    help='Print the modified content of the save-file, with a "tab" separator')
args = parser.parse_args()

BLOCK_SIZE = 6  # When displaying the save-file, print BLOCK_SIZE cols/line. (6 because there are 6 heroes in the game)

offset = 0  # Keep track of the current offset, starting from the beginning of the file

# The separators used when printing the save-file. They must change if the file is used as a CSV file
SEP_GROUPS = '\t'
SEP_COLS = ' '
SEP_CHARS = ''

# Output is a CSV file: we use tabs as separators, they are the only safe choice.
# ',' or ';' cannot be used, they may appear in the 'chars' column, which would
# break the import from the CSV. While Tabs cannot appear in the output.
if args.csv_friendly:
    # SEP_GROUPS = '\t'
    SEP_COLS = '\t'

filename = args.savefile
with open(filename, 'rb') as f, mmap(f.fileno(), 0, access=ACCESS_READ) as mm:
    SAVEFILE_LENGTH = len(mm)

    curr_offset = 0  # Keep track of the current offset, starting from the beginning of the file
    block = 0  # Counter used to separate the values in blocks of size 'BLOCK_SIZE'
    line_offset = 0  # Offset of the first byte in a row (printed in the first column)

    # The blocks to be displayed in the row. These arrays are initialized so that we don't need to bother tracking which
    # must be padded with '_' characters when the number of displayed bytes is < BLOCK_SIZE.
    # This will considerably simplify the Padding (see 'pad' below).
    group_encoded_hexa = ["   _"] * BLOCK_SIZE  # Store encoded hexadecimal values
    group_decoded_hexa = ["   _"] * BLOCK_SIZE  # Store decoded hexadecimal values
    group_decoded_decimal = ["  _"] * BLOCK_SIZE  # Store decoded decimal values
    group_chars = [""] * BLOCK_SIZE  # Store decoded values as characters (most won't make sense)

    # [optional] the file is not always aligned in blocks of 'BLOCK_SIZE', 'pad' can be used to inject a new line to make reading the file easier.
    # An underscore '_' char will be substituted as a padding character.
    # This makes the final result look more regular (as well as easier to parse and document)
    # Note that the pads below do not necessary make sense, on my test safe-file they look good, but it
    # is possible that some fields thought to be unused or related, have in fact another meaning...
    # Content: the offsets that we want to start on a newline.
    pad = {0x1cc, 0x1f1, 0x22c, 0x26f, 0x3a3, 0x430, 0x479}

    for byte_mm in mm:
        byte = byte_mm[0]
        val = dcode(curr_offset, byte)  # => the decoding

        curr_c = "{0:c}".format(val)
        if not str(
                curr_c).isprintable():  # protection against special chars that create problems on the screen (beep, etc.)
            curr_c = "."

        group_encoded_hexa[block] = "{0:#04x}".format(byte)
        group_decoded_hexa[block] = "{0:#04x}".format(val)
        group_decoded_decimal[block] = "{0:>3}".format(val)
        group_chars[block] = curr_c

        # Print & newline when BLOCK_SIZE chars have been parsed or a PADDING/newline byte is reached or the end of file is reached
        if ((block % (BLOCK_SIZE - 1) == 0) and (block > 0)) or (curr_offset in pad) or (
                    curr_offset >= SAVEFILE_LENGTH - 1):
            line_offset = "{0:#05x}".format(line_offset)

            out_format = SEP_GROUPS.join(["{0:6}", "{1}", "{2}", "{3}", "{4}"])
            out = out_format.format(line_offset, SEP_COLS.join(group_encoded_hexa),
                                    SEP_COLS.join(group_decoded_hexa), SEP_COLS.join(group_decoded_decimal),
                                    SEP_CHARS.join(group_chars))
            print(out)
            group_encoded_hexa = ["   _"] * BLOCK_SIZE
            group_decoded_hexa = ["   _"] * BLOCK_SIZE
            group_decoded_decimal = ["  _"] * BLOCK_SIZE
            group_chars = [""] * BLOCK_SIZE
            block = 0
            line_offset = curr_offset + 1  # '+1' because this is the offset of the _next_ byte
        else:
            block += 1

        curr_offset += 1

