#!/usr/bin/python3
import mmap
import operator
import os
import argparse
import sys
import shutil
import time

"""
This script allows the modification of byte values in a Magic Candle 1 save-file.
It can be used to change names, stats, weapons, money, etc.

License: GPLv3

Usage: mc1_modify_savefile.py [-h] -f XXXX.MCS [--dump] [--color-dump]
                              [--out new.MCS]
                              [-m offset byte1 byte2 byte3 [offset byte1 byte2 byte3 ...]]
                              [--stdin] [--csv-friendly]

Modify the save-file by changing some byte values at the specified offsets.

optional arguments:
  -h, --help            show this help message and exit
  -f XXXX.MCS, --savefile XXXX.MCS
                        Name of the savefile (xxxxx.MCS)
  --dump                Print the modified content of the save-file
  --color-dump          Print the modified content of the save-file, with the
                        modified bytes colored
  --out new.MCS         Name of the modified savefile
  -m offset byte1 byte2 byte3 [offset byte1 byte2 byte3 ...], --modify offset byte1 byte2 byte3 [offset byte1 byte2 byte3 ...]
                        List of offset/values to modify Ex: 0x1A3 12 70 50 1
  --stdin               Read from STDIN a list of offset/values to modify (one per line) Ex: 0x2A3 12 70 50
  --csv-friendly        Print the modified content of the save-file, with a
                        "tab" separator

Example (Linux console):
echo 0x0 1 1 1 1 1 1 | python3 mc1_modify_savefile.py -f xxxxx.MCS --stdin --out out.MCS -m 0xf 99 99 99 -m 0xff 55 55
=> this will change the first 6 bytes (set to '1')
   and the 3 bytes starting from the 15th (set to '99')
   and the 2 bytes starting from the 255th (set to '55')

WARNING:
--------
The changed bytes are not visible as such in the save-file, remember, the file is encoded!
To check that the values are OK, use the other script ('mc1_decode_savefile.py'), or open the file
in the game of course. The --dump and --color-dump options also help to validate which
values have been changed.
"""

"""
How the save-file is structured:

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

BLOCK_SIZE = 6  # When displaying the save-file, print BLOCK_SIZE cols/line. (6 because there are 6 heroes in the game)
COLORED_START = "\033[1;36m"  # ASCII code used when displaying the modified bytes in color
COLORED_END = "\033[1;m"  # ASCII code used when displaying the modified bytes in color


def memory_map(filename):  # access=mmap.ACCESS_WRITE):
    """
    Put the whole save-file in memory.
    The bytes can then be accessed as an array.
    """
    fd = os.open(filename, os.O_RDWR)
    fmm = mmap.mmap(fd, 0)
    return fmm


def dump(mm, offset_list_to_color=[], colored_output=False):
    """
    Print the modified content of the save-file. Optionally, with the modified bytes colored.
    :param mm: memory-map of the save-file (allows direct modification)
    :param offset_list_to_color: list of modified offsets
    :param colored_output: if True then the values at the modified offsets (from offset_list_to_color) are displayed with an ASCII color
    :return: nothing
    """
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
        if not str(curr_c).isprintable():  # protection against special chars that create problems on the screen (beep, etc.)
            curr_c = "."

        if colored_output and curr_offset in offset_list_to_color:
            group_encoded_hexa[block] = COLORED_START + "{0:#04x}".format(byte) + COLORED_END
            group_decoded_hexa[block] = COLORED_START + "{0:#04x}".format(val) + COLORED_END
            group_decoded_decimal[block] = COLORED_START + "{0:>3}".format(val) + COLORED_END
            group_chars[block] = COLORED_START + curr_c + COLORED_END
        else:
            group_encoded_hexa[block] = "{0:#04x}".format(byte)
            group_decoded_hexa[block] = "{0:#04x}".format(val)
            group_decoded_decimal[block] = "{0:>3}".format(val)
            group_chars[block] = curr_c

        # Print & newline when BLOCK_SIZE chars have been parsed or a PADDING/newline byte is reached or the end of file is reached
        if ((block % (BLOCK_SIZE - 1) == 0) and (block > 0)) or (curr_offset in pad) or (curr_offset >= SAVEFILE_LENGTH - 1):
            line_offset = "{0:#05x}".format(line_offset)

            out_format = SEP_GROUPS.join(["{0:6}", "{1}", "{2}", "{3}","{4}"])
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


parser = argparse.ArgumentParser(description='Modify the save-file by changing some byte values at the specified offsets.')
parser.add_argument('-f', '--savefile', metavar='XXXX.MCS', help='Name of the savefile (xxxxx.MCS)', required=True)
parser.add_argument('--dump', action='store_true', help='Print the modified content of the save-file')
parser.add_argument('--color-dump', action='store_true',
                    help='Print the modified content of the save-file, with the modified bytes colored')
parser.add_argument('--out', metavar='new.MCS', help='Name of the modified savefile')
parser.add_argument('-m', '--modify', action='append', nargs='+', metavar='offset byte1 byte2 byte3',
                    help='List of offset/values to modify Ex: 0x1A3 12 70 50 1')
parser.add_argument('--stdin', action='store_true',
                    help='Read from STDIN a list of offset/values to modify (one per line) Ex: 0x2A3 12 70 50')
parser.add_argument('--csv-friendly', action='store_true',
                    help='Print the modified content of the save-file, with a "tab" separator')
args = parser.parse_args()
# print(args)

# The separators used when printing the save-file. They must change if the file is used as a CSV file
SEP_GROUPS = '\t'
SEP_COLS = ' '
SEP_CHARS = ''

# Output is a CSV file: we use tabs as separators, they are the only safe choice.
# ',' or ';' cannot be used, they may appear in the 'chars' column, which would
# break the import from the CSV. While Tabs cannot appear in the output.
if args.csv_friendly:
    SEP_GROUPS = '\t'
    SEP_COLS = '\t'

# Load the save-file in memory
if args.out:
    shutil.copyfile(args.savefile, args.out)
    savefile_mm = memory_map(args.out)
else:
    # Directly modify the save-file => first backup it
    suffix = time.strftime('%Y%m%d-%H%M%S')
    shutil.copyfile(args.savefile, args.savefile + "_" + suffix)
    savefile_mm = memory_map(args.savefile)

SAVEFILE_LENGTH = len(savefile_mm)

# Store a list of offsets of all the modified values.
# Used to display them in color when the '--color-dump' option is enabled.
offsets = []

# [option] read offset/values blocks from the '-m' option
if args.modify:
    for modification_group in args.modify:
        if len(modification_group) > 1:
            offset = int(modification_group[0], 16)
            if offset > SAVEFILE_LENGTH:
                print("WARNING: The offsets from this line (%s) are bigger than the length of the file (%s)! Please check them." % (
                      modification_group, hex(SAVEFILE_LENGTH)))
            else:
                for new_val in modification_group[1:]:
                    savefile_mm[offset] = dcode(offset, int(new_val))
                    offsets.append(offset)
                    offset += 1

# [option] read offset/values blocks from STDIN
if args.stdin:
    lines = sys.stdin.readlines()

    for line in lines:
        vals = line.rstrip().split()
        if len(vals) > 1:
            offset = int(vals[0], 16)
            if offset > SAVEFILE_LENGTH:
                print("WARNING: The offsets from this line (%s) are bigger than the length of the file (%s)! Please check them." % (
                      line.rstrip(), hex(SAVEFILE_LENGTH)))
            else:
                for new_val in vals[1:]:
                    savefile_mm[offset] = dcode(offset, int(new_val))
                    offsets.append(offset)
                    offset += 1

# [option] print the content of the modified save-file
if args.dump or args.color_dump:
    if args.csv_friendly:  # no colors! the console chars used to display colors would break the CSV file.
        dump(savefile_mm)
    else:
        dump(savefile_mm, offsets, args.color_dump)

# Write modification to disk
flush_code = savefile_mm.flush()
if flush_code != 0:
   print("ERROR (%d) while writinging the save-file " % flush_code)
else:
    savefile_mm.close()
