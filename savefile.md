# pm4 save file structure

Values labeled as static have not changed once while testing.

Size is in decimal not in hexadecimal.
Offsets are hexadecimal and ansolute unless stated otherwise.

Primitive value types (bool, char, short, int) are always aligned to their size.

The game resets all bytes starting at offset 1d04 to 00 whenever the player
changes the level.

## sections
start inclusive, end exclusive
|from|to  |purpose
|----|----|-------
|0000|0048|save menu overview data
|0048|0148|world map / continue data
|0148|01e0|general stats
|01e0|0e5c|inventory
|0e5c|0ef4|various (more stats? + achievement flags)
|0ef4|19f8|paperization data (museum + regular)
|19f8|1a04|static:0 (most likely just padding for alignment)
|1a04|1fc8|flag and switch arrays
|1fc8|26b0|defeated enemies

## save menu overview data
The game only reads this section for the save selection menu.

|offset|size|purpose
|-|-|-
|0000| 8|save version header = b"\xF6\x04\x33\x01\x14\x07\x00\x00"
|0008| 4|unknown (null)
|000c|16|utf16: "product" + null terminator
|001c| 2|playtime (seconds)
|001e| 1|playtime (minutes)
|001f| 1|playtime (hours)
|0020| 1|collected royal stickers (bitfield) (most likely an int or padded)
|0024| 4|unknown (null)
|0028| 8|timestamp
|0030| 4|reload count
|0034|20|last saved level (used to display level name in save select)

The timestamp is the number of milliseconds since the date 01.01.2000-00:00:00.000
Negative timestamps are handled properly down to 01.01.0001:00:00:00.000

## world map / continue data
This section contains multiple strings which control where to put mario
on the world map. It also stores the level and entrance name for mario to 
continue playing from if the last save was within a level.

|offset|size|purpose|
|-|-|-|
|0048|16|Level name mario appears on on the world map
|0058|64|Name of the map the player saved in
|0098|64|Name of the entrance mario should enter from when continuing
|00d8|16|Unknown Purpose
|00e8|16|Position of the save indicator flag on the world map
|00f8|64|Name of the last battle mario has fought (won or lost) (unknown purpose)

## general stats
|offset|size|purpose
|-|-|-
|0148|4|coin count
|014c|4|health
|0150|4|max health
|0154|4|static:0
|0158|4|static:100
|015c|4|static:1
|0160|4|static:0
|0164|4|static:0
|0168|4|current party member
|016c|4|static:0
|0170|4|Escape chance (percent)
|0174|4|static:0
|0178|4|unknown: value observed in range between 0x00 and 0x60
|017c|4|collected comet pieces
|0180|4|collected royal stickers (bitfield)
|0184|4|abilities (bitfield)
|0188|4|unknown bool
|018c|4|static:0
|0190|4|static:1
|0194|1|unknown bool related to party members in some way
|0195|1|unknown bool related to party members in some way
|0196|2|padding?
|0198|4|static:0
|019c|4|static:1
|01a0|4|unknown bool
|01a4|4|static:0
|01a8|4|static:1
|01ac|4|unknown bool
|01b0|4|static:0
|01b4|4|static:1
|01b8|4|unknown bool
|01bc|4|static:0
|01c0|4|static:1
|01c4|4|unknown bool
|01c8|4|static:0
|01cc|4|static:1
|01d0|4|static:0
|01d4|4|static:0
|01d8|4|static:1
|01dc|4|static:0

### party member enum
32bit int:
|value|equals
|-|-
|-1|no party member
| 0|toad (1-4)
| 1|toad (1-1)
| 2|wiggler piece 1
| 3|wiggler piece 2
| 4|wiggler piece 3
| 5|wiggler piece 4

*NOTE:* The 1-4 toad only shows up in marios party if the flag gf_evt_mac_kinopio_return_town is false

## inventory
|offset|size|purpose
|-|-|-
|01e0|2880|18 inventory pages
|0d20|   4|current album page
|0d24|   4|album page count
|0d28|   4|current scrap page
|0d2c|   4|scrap page count (not entirely sure... may also be hard coded to be 9. Does not change)
|0d30|  40|static:0
|0d58| 256|thing inventory
|0e58|   4|ammount of things in the thing inventory

### inventory page
160 bytes. 150 bytes of 15 consecutive inventory items followed by 10 bytes of padding
#### inventory item
10 bytes. Offsets are relative
|offset|size|purpose
|-|-|-
|0|2|item id
|2|2|unknown
|4|2|item type 
|6|2|x
|8|2|y

### thing inventory
The first *[ThingCount]* ammount of things gets read.
Things without a 3d model crash the game when selected.

#### thing inventory entry
4 bytes. Offsets are relative
|offset|size|purpose
|-|-|-
|0|2|item id
|2|2|unknown

## various (more stats? + achievement flags)
from 0x0e5c to 0x0ef4
|offset|size|purpose
|-|-|-
|0e5c|4|static: 0
|0e60|8|unlocked things
|0e68|4|ammount of battles won within the current level
|0e6c|4|ammount of enemies defeated within the current level
|0e70|4|ammount of bonus coins rewarded on level exit
|0e74|4|static: 0
|0e78|4|ammount of regular stickers donated to the museum
|0e7c|4|ammount of thing stickers donated to the museum
|0e80|4|Achievement: comet pieces collected
|0e84|4|Achievement: secret doors used
|0e88|4|Achievement: sticker collection progress
|0e8c|4|Achievement: hp plus health
|0e90|4|Achievement: coins spent in
|0e94|4|Achievement: battles with perfect
|0e98|4|Achievement: unknown", None
|0e9c|4|Achievement: excellent attack count
|0ea0|4|Achievement: battle spinner jackpot
|0ea4|4|Achievement Goal: comet pieces collected (default: 38)
|0ea8|4|Achievement Goal: secret doors used (default: 35)
|0eac|4|Achievement Goal: sticker collection progress (default: 160)
|0eb0|4|Achievement Goal: hp plus health (default: 100)
|0eb4|4|Achievement Goal: coins spent in shops (default: 10000)
|0eb8|4|Achievement Goal: battles with perfect (default: 500)
|0ebc|4|Achievement Goal: unknown (default: 1000)
|0ec0|4|Achievement Goal: excellent attack count (default: 1000)
|0ec4|4|Achievement Goal: battle spinner jackpot (default: 50)
|0ec8|4|Achievement Delta: comet pieces collected (default: 0)
|0ecc|4|Achievement Delta: secret doors used (default: 0)
|0ed0|4|Achievement Delta: sticker collection progress (default: 0)
|0ed4|4|Achievement Delta: hp plus health (default: 20)
|0ed8|4|Achievement Delta: coins spent in shops (default: 0)
|0edc|4|Achievement Delta: battles with perfect (default: 0)
|0ee0|4|Achievement Delta: unknown (default: 0)
|0ee4|4|Achievement Delta: excellent attack count (default: 0)
|0ee8|4|Achievement Delta: battle spinner jackpot (default: 0)
|0eec|4|unknown; counts up while playing
|0ef0|2|playtime (frames)
|0ef2|1|playtime (minutes)
|0ef3|1|playtime (hours)

Displayed achiement percentages are calculated as (Progress-Offset)/(Goal-Offset)

### unlocked things
Bit field: index controlled by attribute 3 in struct 28 in kdm_item_data.bin
Bitwise indexing like flag table -> see global flags for details

## paperization data (museum + regular)
These arrays are related to paperization and each array entry corresponds to
an array entry in `kdm_pepalyze.bin` and `kdm_pepalyze_museum.bin` respectively.

It does not seem like the game ever reads these arrays, checking the associated
paperization flags instead.

It seems the game fills these arrays with a delay of one paperization. So the
most recent paperization does not appear until the next paperization has
happened.

|offset|size|purpose
|-|-|-
|0ef4| 768|museum paperize data array (192 4byte entries)
|11f4|   4|count of set museum paperize data array entries
|11f8|2048|paperize data array (256 8byte entries)

### museum paperize data entry
I think this array is related to the museum but I am not entirely sure about the
data it stores. The array entries line up with `kdm_pepalyze_museum.bin` but not
always. Donating a sticker to the museum sets the entry with the curresponding
index but not always.

4 bytes each, relative offsets
|offset|size|purpose
|-|-|-
|0|2|most likely array index for kdm_pepalyze_museum.bin
|2|2|`0000` when set, `FF00` when not set


### paperize data entry
Similar to the museum entries but with 2 extra fields.
Paperizations involving map scraps also have array entries but those are never 
set.
|offset|size|purpose
|-|-|-
|0|2|most likely type of paperization but not known exactly
|2|2|array index; identical to kdm_pepalyze.bin struct 21 field 1
|4|2|`0000` when set, `FF00` when not set
|6|2|index of the used item in kdm_item_data.bin, `FFFF` (-1) when not set

## flag and switch arrays
*NOTE*: The end offsets may be inaccurate if the arrays are not entirely filled.
The starting offsets however are correct.

The offsets in `kdm_switch.bin` and `kdm_dispos_data.bin` are relative to the
start of each array so they act more like array indices than offsets.

|start|end|purpose
|-|-|-
|1a04|1b44|global switch array
|1b44|1d04|global flag array
|1d04|1e04|area switch array
|1e04|1fc8|area flag array

### global switch array
Array of 8 bit values referenced in `gsSwitchTable` in `kdm_switch.bin` and some
struct fields in `kdm_dispos_data.bin`.
Script files can reference switches with 8, 16 and 32 bit which combines the
values which follow the referenced switch if more than 8 bit are required. 
Combined switches are stored as big endian numbers.

### global flag array
Array of bits referenced in `gfSwitchTable` in `kdm_switch.bin` and some
struct fields in `kdm_dispos_data.bin`.
Every bit in every byte can be adressed: `byte=int(offset/8)`, `bit=offset%8`

### area switch array
Behaves like global switch array but is cleared on level exit. 
References in `kdm_dispos_data.bin` have 10000 added to identify them as area 
array offsets. To calculate the actual offset, 10000 needs to be subtracted from
the offset again.

### area flag array
Behaves like global flag array but is cleared on level exit. 
References in `kdm_dispos_data.bin` have 10000 added to identify them as area 
array offsets. To calculate the actual offset, 10000 needs to be subtracted from
the offset again.

## defeated NPCs (todo: check for other stored info?)
*NOTE* This section is cleared on every level exit.
0x1fc8 to 0x26b0 (EOF). 104 bytes per entry, 17 entries total (1768 bytes)
Each entry describes one map. 
Entries start with a null terminated string which is the map name, padded with 
null bytes to be 4 byte aligned.  
This is followed by 4-byte-aligned 32bit integers which correspond to the 19th
entry in struct 34 defined in `kdm_dispos_data.bin`.
If an NPC's id is stored in this entry, it will not be spawned when the entry's 
corresponding map is loaded.

The remaining bytes of the entry are just zeroed out so the to make the entry 
104 bytes in total. 
