#!/usr/bin/python3
import sys
from mmap import ACCESS_READ, mmap
import operator

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

offset = 0  # Keep track of the current offset, starting from the beginning of the file
block = 0  # Counter used to separate the values in blocks of 6
group_encoded_hexa = ''  # Store encoded hexadecimal values
group_decoded_hexa = ''  # Store decoded hexadecimal values
group_decoded_decimal = ''  # Store decoded decimal values
group_chars = ''  # Store decoded values as characters (most won't make sense)

# [optional] the file is not always aligned in blocks of 6, 'pad' can be used to inject a new line to make reading the file easier.
# An underscore '_' char will be substituted as a padding character.
# This makes the final result look more regular (as well as easier to parse and document)
# Format: the offset where we want to add a newline and the number of padding characters to insert (from 1 to 5 max).
pad = {0x1f1: 1, 0x270: 5, 0x3a4: 4}

filename = sys.argv[1]

with open(filename, 'rb') as f, mmap(f.fileno(), 0, access=ACCESS_READ) as mm:
    for byte in mm:  # Length is equal to the current file size

        # Add artificial padding & newline at the Offsets defined in 'pad'
        if offset in pad:
            block += pad[offset]
            for i in range(pad[offset]):
                group_encoded_hexa = '	'.join((group_encoded_hexa, "{0:>4}".format("_")))
                group_decoded_hexa = '	'.join((group_decoded_hexa, "{0:>4}".format("_")))
                group_decoded_decimal = '	'.join((group_decoded_decimal, "{0:>3}".format("_")))
                group_chars += "_"

        val = operator.xor((offset + 0xA5), byte[0])  # => the decoding

        # Print & newline when 6 chars have been parsed
        if (block % 6 == 0) and (block > 0):

            # The line_offset is the first displayed field. It must take into account the possible padding characters
            # (they must be ignored).
            if offset in pad:
                line_offset = hex(offset - 6 + pad[offset])
            else:
                line_offset = hex(offset - 6)

            out = "{0:6}	{1}	{2}	{3} {4}".format(line_offset, group_encoded_hexa, group_decoded_hexa, group_decoded_decimal, group_chars)
            print(out)
            group_encoded_hexa = ''
            group_decoded_hexa = ''
            group_decoded_decimal = ''
            group_chars = ''

        # Concat the current block results
        group_encoded_hexa = '	'.join((group_encoded_hexa, "{0:#04x}".format(byte[0])))
        group_decoded_hexa = '	'.join((group_decoded_hexa, "{0:#04x}".format(val & 0xFF)))
        group_decoded_decimal = '	'.join((group_decoded_decimal, "{0:>3}".format(val & 0xFF)))

        curr_c = "{0:c}".format(val & 0xFF)
        if not str(
                curr_c).isprintable():  # protection against special chars that create problems on the screen (beep, etc.)
            curr_c = "."
        group_chars = group_chars + curr_c

        offset += 1
        block += 1

