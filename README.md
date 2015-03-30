# magic-candle-1-reverse-eng
Reverse engineering of the old DOS game 'The Magic Candle 1' (1989)
===============================================================

https://en.wikipedia.org/wiki/Magic_Candle

The Magic Candle is an old RPG videogame from 1989 with 2 sequels (hence the '1', added for clarification).

Game screenshot:

![Castle map example](https://github.com/lglearn/magic-candle-1-reverse-eng/blob/master/mc1_map_castle.png "Castle screenshot")

Game screenshot:

![Outside map example](https://github.com/lglearn/magic-candle-1-reverse-eng/blob/master/mc1_map_outside.png "Map screenshot")

Some context
------------

Although I've had the game for years, I had not played it until recently (on the DOSBox emulator). As an old gamer, I know only too well how these old games are usually HARD and unforgiving, especially at the beginning of the game. 

Being annoyed after getting my party slaughtered 3 times in less than an hour, I searched a tool to buff my stats, in order to go further in the game as I wanted to get a feeling of the game before investing a lot of time on it. Unfortunately, I did not find anything interesting. No tool nor description of the save-file format, which would have enabled me to manually change my characters stats (with the good ol' hexadecimal editor).

Disappointed, I decided to reverse engineer the save-file myself.

This ended up as being much more challenging than expected...

The Save-file format & decoder
------------------------------

Basically, the file is encoded with a simple method (XOR <magic value> + offset) but it makes modifications to the save file _very_ annoying!

I have already modified game save-files in the past (Might & Magic 1 for instance), but this one was much more difficult, even the fields organization was different from what I expected.

The fact that the game runs under DOS does not help (there are not as many tools, thanks for the DOSBox debug feature, it sure helped!), and I couldn't rely on the disassembly of the game since I only know the basics of x86 assembler and the result of the disassembler seems wrong (though I'm not 100% sure). Which means that I had to rely on the good old 'modify/reload' try and error tactic. Very time consuming, very frustrating.

I first wrote a decoder, then started analysing the impact of each byte change on the gameplay.

After hundreds of tries, I've managed to discover the signification of most of the interesting stats hidden in the file (see 'savefile_decoding' in the repository).

Tiles decoder
-------------

I've also played a bit with the tiles and tried to rebuild the maps. For the fun of it.

The decoding of the tiles basically works (see 'tiles_decoding' in the repository). Most files can be decoded, and you get the tiles used by the game. There are still a few problems with 2 of the tiles files, but I did not examine them in detail.

The TILE format is detailled in the Python decoder.

Here is a -concatenated- example of the tiles extracted from the file EGA18.TIL:
![Tiles example](https://github.com/lglearn/magic-candle-1-reverse-eng/blob/master/tiles_decoding/EGA18.TIL__extracted_tiles.png)

Map decoder
-----------

As for the maps, this is a much harder problem: my understanding is that the maps in fact also contain game data (text, 'scripted' actions, etc.) and their decoding is not that easy. I managed to decode one fairly easily (a map is simply a set of tiles) but most others do not work.

The map decoder is not yet published in the repository.

In the hope it will be useful
-----------------------------

I've at last published the results of my musings with this game. I hope it'll be useful to others. I know it would have helped me :-)
