#! /usr/bin/env python3

import os
import sys
import struct
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter import messagebox

TOOLTIPS_ENABLED = True
if TOOLTIPS_ENABLED:
    try:
        from idlelib.tooltip import Hovertip
    except:
        print("importing tooltips failed. Is idle installed?")
        TOOLTIPS_ENABLED = False

# TODO: clean up
# NOTE: Setting the inventory items to values of the wrong type will likely crash the game

# config
CHECK_LIMITS: bool = False
TEMP_ITEM_TYPES: dict[int, int] = {0:0,1:0,2:0,3:65534}
DROPDOWN_WIDTHS = 56

# constants
SAVE_GS_START = 0x1a04
SAVE_GF_START = 0x1b44
SAVE_AS_START = 0x1d04
SAVE_AF_START = 0x1e04
SAVE_ITEM_AS_START = 0x1d04 # TODO: DOUBLE_CHECK FOR STICKER LISTS (??????)
SAVE_ITEM_AF_START = 0x1e04 # TODO: DOUBLE_CHECK FOR STICKER LISTS (0x1e04)
ITEM_PAGE_BASE_OFFSET: int = 0x01e0
ITEM_PAGE_ITEM_COUNT: int = 15
ITEM_PAGE_SIZE: int = 160

root: tk.Tk = tk.Tk()

ITEM_PAGES: list[str] = []
ITEM_NAMES: list[str] = []
ITEM_INDEX_LOOKUP: dict[str, int] = {}
ITEM_TYPES: dict[str, int] = {}
FLAG_OFFSETS: dict[str, tuple[int,int]] = {}
SWITCH_OFFSETS: dict[str, int] = {}

MOBJ_FLAG_OFFSETS: dict[str, tuple[int,int]] = {}
MOBJ_SWITCH_OFFSETS: dict[str, int] = {}
ITEM_FLAG_OFFSETS: dict[str, tuple[int, int]] = {}
ITEM2_SWITCH_OFFSETS: dict[str, int] = {}
ITEM2_FLAG_OFFSETS: dict[str, tuple[int, int]] = {}
# temp
AS_OFFSETS: dict[str, int] = {}
AF_OFFSETS: dict[str, tuple[int,int]] = {}
A_MOBJ_FLAG_OFFSETS: dict[str, tuple[int,int]] = {}
A_MOBJ_SWITCH_OFFSETS: dict[str, int] = {}
A_ITEM_FLAG_OFFSETS: dict[str, tuple[int, int]] = {}
A_ITEM2_SWITCH_OFFSETS: dict[str, int] = {}
A_ITEM2_FLAG_OFFSETS: dict[str, tuple[int, int]] = {}
# read map info from kdm files
MAP_NAME_LIST = []
MAP_NAMES: dict[str, list[str]] = {}
ENTRANCE_NAMES: dict[str, list[str]] = {}
ENCOUNTER_NAME_LIST: list[str] = [""]

STRING_TYPE_LEVEL_REF_SELECT = -1
STRING_TYPE_LEVEL_REF = 0
STRING_TYPE_MAP_REF = 1
STRING_TYPE_ENTRANCE_REF = 2
STRING_TYPE_BATTLE_REF = 3
# type, offset, name, max length (including null terminator), tooltip
STRING_OFFSETS: tuple[tuple[int, int, str, int, str], ...] = (
    (STRING_TYPE_LEVEL_REF, 0x0034, "SaveMenuLevelName", 16, "level name displayed in the save selection screen"),
    (STRING_TYPE_LEVEL_REF, 0x0048, "WorldMapPlaceName", 16, "level to spawn mario at on the overworld"),
    (STRING_TYPE_LEVEL_REF, 0x00e8, "SaveFlagLocation", 16, "level the save indicator flag is placed at"),
    # TEMP: use this to determine which map to select
    (STRING_TYPE_LEVEL_REF, 0x00d8, "Unknown", 16, "unknown purpose"),
    # out of order but more elegant to implement
    (STRING_TYPE_LEVEL_REF_SELECT, 0x0000, "MapLoadLevelSelect (not saved)", 16, "select level to spawn mario in"),
    (STRING_TYPE_MAP_REF, 0x0058, "MapLoadName", 64, "map mario continues in"),
    (STRING_TYPE_ENTRANCE_REF, 0x0098, "MapLoadEntranceName", 64, "entrance mario spawns at"),
    (STRING_TYPE_BATTLE_REF, 0x00f8, "LastBattle", 64, "last encounter mario fought"),
)

TEMP = ["check", "map_tst", "tmp", "tor_1", "tst", "wld"]
TEMP2 = ["ETT", "TST"]
TEMP3 = ["TST"]
def init_options():
    import kdm
    global ENTRANCE_NAMES, MAP_NAMES, MAP_NAME_LIST

    DATAPATH = askdirectory(parent=root, initialdir=DEFAULT_DATA_PATH, title="Select data directory")

    # link data
    LINK_DATA = kdm.load(f"{DATAPATH}/kdm_link_data.bin")
    for area in LINK_DATA["link_data_all"]["<KdmArrayValues>"]:
        area = area["<KdmArrayValues>"][0]
        ENTRANCE_NAMES[area["Name"]] = []
        for link in area["Links"]["<KdmArrayValues>"]:
            link = link["<KdmArrayValues>"][0]
            ENTRANCE_NAMES[area["Name"]].append(link["FromDoor"])
    
    WORLDMAP_DATA = kdm.load(f"{DATAPATH}/kdm_mapdata.bin")
    for area in WORLDMAP_DATA["mapDataTable"]["<KdmArrayValues>"]:
        area = area["<KdmArrayValues>"][0]
        if area["ModelPath"] is not None:
            temp = area["ModelPath"].split("/")[0]
            if temp in TEMP:
                continue
        else:
            continue
        if area["ScriptPath"] is not None:
            temp = area["ScriptPath"].split("/")[0]
            if temp in TEMP2:
                continue
        if area["Level"] in TEMP3:
            continue
        if area["Level"] not in MAP_NAMES:
            MAP_NAMES[area["Level"]] = []
        MAP_NAMES[area["Level"]].append(area["Name"])
    
    MAP_NAME_LIST = [k for k in MAP_NAMES.keys()]

    ITEM_NAMES.clear()
    ITEM_INDEX_LOOKUP["[EMPTY]"] = -1
    #ITEM_NAMES.append("[EMPTY]")
    ITEMS = kdm.load(f"{DATAPATH}/kdm_item_data.bin")
    for i, item in enumerate(ITEMS["ItemDataSaveList"]["<KdmArrayValues>"]):
        item = item["<KdmArrayValues>"][0]
        ITEM_NAMES.append(item["Name"])
        ITEM_INDEX_LOOKUP[item["Name"]] = i
        ITEM_TYPES[item["Name"]] = item["ItemVariant"]["VariantTypeEnum"]
    for i in range(8):
        ITEM_PAGES.append(f"StickerPage{i+1}")
    for i in range(9):
        ITEM_PAGES.append(f"ScrapPage{i+1}")
    for i in range(1):
        ITEM_PAGES.append(f"Unknown{i}")

    # flags
    flaginfo = kdm.load(f"{DATAPATH}/kdm_switch.bin")
    for flag in flaginfo["gfSwitchTable"]["<KdmArrayValues>"]:
        if flag["Name"].__contains__("_mobj_item_"): continue # dummy?
        FLAG_OFFSETS[flag["Name"]] = (SAVE_GF_START + flag["Offset"] // 8, flag["Offset"] % 8)
    for switch in flaginfo["gsSwitchTable"]["<KdmArrayValues>"]:
        if switch["Name"].__contains__("_mobj_item_"): 
            continue # dummy?
        SWITCH_OFFSETS[switch["Name"]] = SAVE_GS_START + switch["Offset"]
    for switch in flaginfo["asSwitchTable"]["<KdmArrayValues>"]:
        if switch["Name"].__contains__("_mobj_item_"): 
            continue # dummy?
        AS_OFFSETS[switch["Name"]] = SAVE_AS_START + switch["Offset"]
    # NOTE: THESE ARE MAP SPECIFIC
    for flag in flaginfo["afSwitchTable"]["<KdmArrayValues>"]:
        if flag["Name"].__contains__("_mobj_item_"): continue # dummy?
        AF_OFFSETS[flag["Name"]] = (SAVE_AF_START + flag["Offset"] // 8, flag["Offset"] % 8)
    
    disposdata = kdm.load(f"{DATAPATH}/kdm_dispos_data.bin")
    for level in disposdata["all_disposDataTbl"]["<KdmArrayValues>"]:
        if level is None: break # null terminator
        level = level["<KdmArrayValues>"][0]
        if level["Name"] in ["CHECK", "TST"]: continue # debugging levels
        for encounter in level["Encounters"]["<KdmArrayValues>"]:
            if encounter is None: break # null terminator
            encounter = encounter["<KdmArrayValues>"][0]
            ENCOUNTER_NAME_LIST.append(encounter["Elements"]["<KdmArrayValues>"][0]["Name"])

        for area in level["MapObjects"]["<KdmArrayValues>"]:
            if area is None: break # null terminator
            area = area["<KdmArrayValues>"][0]
            for obj in area["MapObjects"]["<KdmArrayValues>"]:
                if obj is None: break # null terminator
                if obj["FlagOffset"] != -1:
                    offset = obj["FlagOffset"]
                    # offsets < 10000 are stored in gfData (i think?)
                    if offset < 10000:
                        MOBJ_FLAG_OFFSETS[f'{level["Name"]} {area["Map"]} {obj["Type"]} {obj["Name"]}'] = (SAVE_GF_START + offset // 8, offset % 8)
                    # offsets > 10000 are stored in afData (i think?)
                    else:
                        offset = offset % 10000
                        A_MOBJ_FLAG_OFFSETS[f'{level["Name"]} {area["Map"]} {obj["Type"]} {obj["Name"]}'] = (SAVE_AF_START + offset // 8, offset % 8)

                if obj["SwitchOffset"] != -1:
                    offset = obj["SwitchOffset"]
                    # offsets < 10000 are stored in gsData (i think?)
                    if offset < 10000:
                        MOBJ_SWITCH_OFFSETS[f'{level["Name"]} {area["Map"]} {obj["Type"]} {obj["Name"]}'] = SAVE_GS_START + offset
                    else:
                        offset = offset % 10000
                        A_MOBJ_SWITCH_OFFSETS[f'{level["Name"]} {area["Map"]} {obj["Type"]} {obj["Name"]}'] = SAVE_AS_START + offset
                    # offsets > 10000 are stored in asData (i think?)
        for area in level["MapItems"]["<KdmArrayValues>"]:
            if area is None: break # null terminator
            area = area["<KdmArrayValues>"][0]
            for item in area["Items"]["<KdmArrayValues>"]:
                if item is None: break # null terminator
                if item["FlagOffset"] != -1:
                    offset = item["FlagOffset"]
                    # offsets < 10000 are stored in gfData (i think?)
                    if offset < 10000:
                        ITEM_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {item["Type"]} {item["Name"]}'] = (SAVE_GF_START + offset // 8, offset % 8)
                    else:
                        offset = offset % 10000
                        A_ITEM_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {item["Type"]} {item["Name"]}'] = (SAVE_AF_START + offset // 8, offset % 8)
                    # offsets > 10000 are stored in afData (i think?)
                if item["TypeList"] is not None:
                    typelist = item["TypeList"]["<KdmArrayValues>"][0]
                    offset1 = typelist["SwitchOffset"]
                    if offset1 < 10000: # gs?
                        ITEM2_SWITCH_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = SAVE_GS_START + offset1
                    else:
                        offset1 = offset1 % 10000
                        A_ITEM2_SWITCH_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = SAVE_ITEM_AS_START + offset1
                    offset2 = typelist["FlagOffset"]
                    if offset2 < 10000: # gf?
                        ITEM2_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = (SAVE_GF_START + offset2 // 8, offset2 % 8)
                    else:
                        offset2 = offset2 % 10000
                        A_ITEM2_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = (SAVE_ITEM_AF_START + offset2 // 8, offset2 % 8)
GLOBAL_NAMES: list[str] = ["ENCOUNTER_NAME_LIST", "ITEM_PAGES", "ITEM_NAMES", "ITEM_INDEX_LOOKUP", "ITEM_TYPES", "FLAG_OFFSETS", "SWITCH_OFFSETS", "MOBJ_FLAG_OFFSETS", "MOBJ_SWITCH_OFFSETS", "ITEM_FLAG_OFFSETS", "ITEM2_SWITCH_OFFSETS", "ITEM2_FLAG_OFFSETS", "AS_OFFSETS", "AF_OFFSETS", "A_MOBJ_FLAG_OFFSETS", "A_MOBJ_SWITCH_OFFSETS", "A_ITEM_FLAG_OFFSETS", "A_ITEM2_SWITCH_OFFSETS", "A_ITEM2_FLAG_OFFSETS", "MAP_NAME_LIST", "MAP_NAMES", "ENTRANCE_NAMES"]
CONSTANT_JSON_PATH = __file__.replace(".py", "_constants.json")
def init_options_pregenerated():
    import json
    with open(CONSTANT_JSON_PATH, "r") as f: 
        constants = json.load(f)
    globals_dict = globals()
    for g in GLOBAL_NAMES:
        globals_dict[g] = constants[g]


def dump_constants():
    import json
    result = {}
    globals_dict = globals()
    for g in GLOBAL_NAMES:
        result[g] = globals_dict[g]

    with open(CONSTANT_JSON_PATH, "w") as f: 
        # add an indent to be friendlier to git if minor changes occur
        constants = json.dump(result, f, ensure_ascii=False) #, indent=1)

if os.name == "nt":
    EMULATOR_PATH = os.environ["APPDATA"] + "\\Azahar\\"
    if not os.path.isdir(EMULATOR_PATH):
        EMULATOR_PATH = os.environ["APPDATA"] + "\\Citra\\"
    DATA_SUFFIX = "\\dump\\romfs\\00040000000A5F00\\Data\\"
    SAVE_SUFFIX = "\\sdmc\\Nintendo 3DS\\00000000000000000000000000000000\\00000000000000000000000000000000\\title\\00040000\\000a5f00\\data\\00000001\\"
else:
    # azahar flatpak support only for now
    EMULATOR_PATH = os.environ["HOME"] + "/.var/app/org.azahar_emu.Azahar/data/azahar-emu/"
    DATA_SUFFIX = "dump/romfs/00040000000A5F00/Data/"
    SAVE_SUFFIX = "sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/000a5f00/data/00000001/"
DEFAULT_DATA_PATH = EMULATOR_PATH + DATA_SUFFIX if os.path.isdir(EMULATOR_PATH) else None
DEFAULT_SAVE_PATH = EMULATOR_PATH + SAVE_SUFFIX if os.path.isdir(EMULATOR_PATH) else None

# cache results instead of parsing all files every time
# TODO: display info popup if json file is missing
if (len(sys.argv) > 1 and sys.argv[1] == "dumpconstants"): 
    init_options()
    dump_constants()
elif not os.path.isfile(CONSTANT_JSON_PATH):
    messagebox.showerror("missing saveedit_constants.json", "Can not find constants json file. Please download it or select the data directory of a sticker star rom dump to generate it now.", type=messagebox.OKCANCEL)
    init_options()
    dump_constants()
else:
    init_options_pregenerated()

CHANGE_CALLBACKS: list = []
INIT_CALLBACKS: list = []
OPENED_PATH: str = ""
def load_path():
    filename = askopenfilename(parent=root, title="select save file", initialdir=DEFAULT_SAVE_PATH, initialfile = "pm4_0.bin")
    load_data(filename)
def load_data(filename: str):
    global DATA, save_button, OPENED_PATH
    if filename is not None and filename != () and filename != "":
        with open(filename, "rb") as f:
            DATA = bytearray(f.read())
    else:
        return
    if len(DATA) == 0:
        return
    OPENED_PATH = filename
    save_button['state'] = 'normal'
    for callback in INIT_CALLBACKS:
        callback()
    for i, ref in enumerate(STRINGREFS):
        STRINGREFS[i][0]['state'] = 'normal'
        s = read_string(i)
        if i < 4:
            s = s.upper()
        STRINGREFS[i][0].set(s)
    if STRINGREFS[5][0].get() == "wld":
        STRINGREFS[4][0].set("WLD")
    else:
        STRINGREFS[4][0].set(STRINGREFS[3][0].get())

def save_path():
    global DATA, OPENED_PATH
    path_parts = OPENED_PATH.replace("\\", "/").split("/")
    # ensure all data has been saved
    for callback in CHANGE_CALLBACKS:
        callback()
    for i, ref in enumerate(STRINGREFS):
        write_string(i, STRINGREFS[i][0].get())
    # player saved on world map insted of in level
    write_bool(0x0144, 0, STRINGREFS[5][0].get() == "wld")
    filename = asksaveasfilename(parent=root, title="select save file", initialdir="/".join(path_parts[:-1]), initialfile = path_parts[-1])
    if filename is not None and filename != () and filename != "":
        with open(filename, "wb") as f:
            f.write(DATA)
SIGNED_INT_NAMES = (None, "<b", "<h", None, "<i", None, None, None, "<q")
UNSIGNED_INT_NAMES = (None, "<B", "<H", None, "<I", None, None, None, "<Q")

SIGNED_INT_RANGES = (None, (-128, 127), (-32768, 32767), None, (-2147483648, 2147483647), None, None, None, (-9223372036854775808, 9223372036854775807))
UNSIGNED_INT_RANGES = (None, (0, 255), (0, 65535), None, (0, 4294967295), None, None, None, (0, 18446744073709551615))

# window setup
root.title("sticker star save editor")
#root.resizable(False, False)
root.geometry("662x604")
#for i in range(6): root.columnconfigure(i, weight=1)
root.columnconfigure(2, weight=1)
root.rowconfigure(1, weight=1)

def read_bool(offset: int, index: int) -> bool:
    return (DATA[offset] >> index) % 2 != 0
def write_bool(offset: int, index: int, value: bool):
    old_value = DATA[offset]
    # remove bit at index
    new_value = (old_value & (~(1 << index))) & 0xFF
    if value:
        new_value |= 1 << index
    DATA[offset] = new_value
def read_uint(offset: int, bytecount:int = 1) -> int:
    result = 0
    for i in range(bytecount):
        result += DATA[offset + i] << 8 * i
    return result
def write_uint(offset: int, value: int, bytecount: int = 1):
    for i in range(bytecount):
        DATA[offset + i] = value % 256
        value = value >> 8
def read_int(offset: int, bytecount:int = 1) -> int:
    return struct.unpack_from(SIGNED_INT_NAMES[bytecount], DATA, offset)[0]
def write_int(offset: int, value: int, bytecount: int = 1):
    struct.pack_into(SIGNED_INT_NAMES[bytecount], DATA, offset, value)

file_controls = ttk.Frame(root)

# widget setup
load_button = ttk.Button(file_controls, command=load_path, text="load file")
load_button.grid(row=0, rowspan=1, column=0, columnspan=1)
save_button = ttk.Button(file_controls, command=save_path, text="save file")
save_button.grid(row=0, rowspan=1, column=1, columnspan=1) # column=13
save_button['state'] = 'disabled'
#file_controls.pack(anchor="nw")
file_controls.grid(row=0, column=0, sticky="nw")

def property_int(root, row: int, col: int, name: str, offset: int, 
bytecount: int = 2, signed: bool = False, min: None|int = None, max: None|int = None, 
tooltip: None|str=None, padding:int = 0):
    has_name = name is not None and name != ""
    if has_name: ttk.Label(root, text=name).grid(row=row, column=col, columnspan=1+padding)
    else: col -= 1
    value = tk.StringVar()
    value_range = (SIGNED_INT_RANGES if signed else UNSIGNED_INT_RANGES)[bytecount]
    if CHECK_LIMITS:
        value_range = (value_range[0] if min is None else min, value_range[1] if max is None else max)
    spinbox = ttk.Spinbox(root, from_=value_range[0], to=value_range[1], textvariable=value, width=11)
    if TOOLTIPS_ENABLED and tooltip is not None:
        Hovertip(spinbox, tooltip)
    spinbox.grid(row=row, column=col+1 + padding*2, columnspan=1+padding)
    spinbox["state"] = "disabled"
    def save(): 
        v = value.get()
        t = v.removeprefix("-")
        if t.isascii() and t.isnumeric():
            i = int(v)
            if signed:
                write_int(offset, i, bytecount)
            else:
                write_uint(offset, i, bytecount)
    def load():
        nonlocal spinbox
        spinbox["state"] = "normal"
        value.set(str(read_int(offset, bytecount) if signed else read_uint(offset, bytecount)))
    CHANGE_CALLBACKS.append(save)
    INIT_CALLBACKS.append(load)
def property_boolean(root, row: int, col: int, name: str, offset: int, index: int, thin: bool, tooltip:None|str = None):
    value = tk.BooleanVar()
    checkbox = ttk.Checkbutton(root, text=name, variable=value)
    checkbox.grid(row=row, column=col, columnspan=2 if not thin else 1)
    checkbox["state"] = "disabled"
    if TOOLTIPS_ENABLED and tooltip is not None:
        Hovertip(checkbox, tooltip)
    def save(): 
        write_bool(offset=offset, index=index, value=value.get())
    def load():
        nonlocal checkbox, value
        checkbox["state"] = "normal"
        value.set(read_bool(offset=offset, index=index))
    CHANGE_CALLBACKS.append(save)
    INIT_CALLBACKS.append(load)

COLUMN_WRAP = 6
CURRENT_ROW = 2
CURRENT_COL = 0

tabs = ttk.Notebook(root)
tabs.grid(row=1,column=0, sticky="ewns", columnspan=3)
#tabs.pack(anchor="nw", fill="both") # (fill="both") # .grid(row=1, column=0, columnspan=3)

CURRENT_TAB_ROOT = root
WINDOW_TABS = []

def category_tab(name: str, insert_at: int = -1):
    global CURRENT_TAB_ROOT, WINDOW_TABS
    CURRENT_TAB_ROOT = ttk.Frame(tabs)
    if insert_at != -1:
        tabs.insert(insert_at, CURRENT_TAB_ROOT, text=name)
    else:
        tabs.add(CURRENT_TAB_ROOT, text=name)
    WINDOW_TABS.append(CURRENT_TAB_ROOT)
    tabs.select(0) # temp

# temporary helpers
def property_uint(offset: int, bytes: int, name: str, tooltip: None|str=None, min: None|int = None, max: None|int = None, padding: int=0):
    global CURRENT_TAB_ROOT, CURRENT_COL, CURRENT_ROW
    property_int(CURRENT_TAB_ROOT, CURRENT_ROW, CURRENT_COL, name, offset, bytes, False, tooltip=tooltip, padding=padding)
    CURRENT_ROW += 1
def property_sint(offset: int, bytes: int, name: str, tooltip: None|str=None, min: None|int = None, max: None|int = None, padding: int=0):
    global CURRENT_TAB_ROOT, CURRENT_COL, CURRENT_ROW
    property_int(CURRENT_TAB_ROOT, CURRENT_ROW, CURRENT_COL, name, offset, bytes, True, tooltip=tooltip, padding=padding)
    CURRENT_ROW += 1
def property_bool(offset: int, index: int, name: str, tooltip: None|str=None, thin: bool = False):
    global CURRENT_TAB_ROOT, CURRENT_COL, CURRENT_ROW
    property_boolean(CURRENT_TAB_ROOT, CURRENT_ROW, CURRENT_COL, name, offset, index, thin, tooltip=tooltip)
    CURRENT_ROW += 1
def category(col: int, row: int, name: str, tooltip: None|str=None, columnspan: int = 2):
    global CURRENT_TAB_ROOT, CURRENT_COL, CURRENT_ROW
    CURRENT_COL = col
    CURRENT_ROW = row
    if row >= 0 and name is not None and name != "":
        label = ttk.Label(CURRENT_TAB_ROOT, text=name)
        label.grid(row=row, column=col, columnspan=columnspan)
        if TOOLTIPS_ENABLED and tooltip is not None:
            Hovertip(label, tooltip)
    CURRENT_ROW += 1

def property_date(row=1, col=0, offset=0x0028):
    import datetime as dt
    # the timestamp format is the ammount of milliseconds since 2000.01.01-00:00
    DATE_REFERENCE = dt.datetime(year=2000, month=1, day=1)
    ttk.Label(CURRENT_TAB_ROOT, text="save timestamp").grid(row=row, column=col, columnspan=2)
    ttk.Label(CURRENT_TAB_ROOT, text="year").grid(row=row + 1, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="month").grid(row=row + 2, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="day").grid(row=row + 3, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="hour").grid(row=row + 4, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="minute").grid(row=row + 5, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="second").grid(row=row + 6, column=col)
    ttk.Label(CURRENT_TAB_ROOT, text="millisecond").grid(row=row + 7, column=col)
    milliseconds_total = 0
    year_value = tk.StringVar()
    month_value = tk.StringVar()
    day_value = tk.StringVar()
    hour_value = tk.StringVar()
    minute_value = tk.StringVar()
    second_value = tk.StringVar()
    millisecond_value = tk.StringVar()
    year_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=year_value, width=11, from_=1, to=9999) #from_=SIGNED_INT_RANGES[8][0], to=SIGNED_INT_RANGES[8][1])
    month_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=month_value, width=11, from_=1, to=12)
    day_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=day_value, width=11, from_=1, to=31)
    hour_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=hour_value, width=11, from_=0, to=24)
    minute_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=minute_value, width=11, from_=0, to=59)
    second_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=second_value, width=11, from_=0, to=59)
    millisecond_box = ttk.Spinbox(CURRENT_TAB_ROOT, textvariable=millisecond_value, width=11, from_=0, to=999)
    year_box.grid(row=row + 1, column=col+1)
    month_box.grid(row=row + 2, column=col+1)
    day_box.grid(row=row + 3, column=col+1)
    hour_box.grid(row=row + 4, column=col+1)
    minute_box.grid(row=row + 5, column=col+1)
    second_box.grid(row=row + 6, column=col+1)
    millisecond_box.grid(row=row + 7, column=col+1)
    year_box["state"] = "disabled"
    month_box["state"] = "disabled"
    day_box["state"] = "disabled"
    hour_box["state"] = "disabled"
    minute_box["state"] = "disabled"
    second_box["state"] = "disabled"
    millisecond_box["state"] = "disabled"
    def save():
        year = year_value.get()
        if not year.isascii() or not year.isnumeric(): return
        year = int(year)
        month = month_value.get()
        if not month.isascii() or not month.isnumeric(): return
        month = int(month)
        day = day_value.get()
        if not day.isascii() or not day.isnumeric(): return
        day = int(day)
        hour = hour_value.get()
        if not hour.isascii() or not hour.isnumeric(): return
        hour = int(hour)
        minute = minute_value.get()
        if not minute.isascii() or not minute.isnumeric(): return
        minute = int(minute)
        second = second_value.get()
        if not second.isascii() or not second.isnumeric(): return
        second = int(second)
        millisecond = millisecond_value.get()
        if not millisecond.isascii() or not millisecond.isnumeric(): return
        millisecond = int(millisecond)

        target_date = dt.datetime(year, month, day, hour, minute, second, millisecond * 1000)

        milliseconds_total = int((target_date - DATE_REFERENCE) / dt.timedelta(milliseconds=1))
        write_int(offset, milliseconds_total, 8)
    def load():
        nonlocal year_box, month_box, day_box, hour_box, minute_box, second_box, millisecond_box, milliseconds_total
        milliseconds_total = read_int(offset, 8)
        negative = milliseconds_total < 0
        if negative:
            milliseconds_total *= -1
        delta = dt.timedelta(milliseconds=milliseconds_total)
        if negative:
            date = DATE_REFERENCE - delta
        else:
            date = DATE_REFERENCE + delta

        year_value.set(str(date.year))
        month_value.set(str(date.month))
        day_value.set(str(date.day))
        hour_value.set(str(date.hour))
        minute_value.set(str(date.minute))
        second_value.set(str(date.second))
        millisecond_value.set(str(date.microsecond // 1000))

        year_box["state"] = "normal"
        month_box["state"] = "normal"
        day_box["state"] = "normal"
        hour_box["state"] = "normal"
        minute_box["state"] = "normal"
        second_box["state"] = "normal"
        millisecond_box["state"] = "normal"
    CHANGE_CALLBACKS.append(save)
    INIT_CALLBACKS.append(load)

def on_level_changed(index, value, op):
    global STRINGREFS
    level = STRINGREFS[4][1].get()
    STRINGREFS[5][0]["values"] = MAP_NAMES[level] if level in MAP_NAMES else ["wld"]
    STRINGREFS[5][0].current(0)
def on_map_changed(index, value, op):
    global STRINGREFS
    current_room = STRINGREFS[5][1].get()
    if current_room in ENTRANCE_NAMES:
        STRINGREFS[6][0]["values"] = ENTRANCE_NAMES[current_room]
    elif current_room == "wld":
        STRINGREFS[6][0]["values"] = [""]
    else:
        STRINGREFS[6][0]["values"] = ["ERROR"]
    STRINGREFS[6][0].current(0)

def read_string(index: int) -> str:
    global STRING_OFFSETS, DATA
    offset = STRING_OFFSETS[index][1]
    if offset == 0: return ""
    maxlen = STRING_OFFSETS[index][3]
    length = 0
    while length <= maxlength and DATA[offset + length] != 0:
        length += 1
    if length > maxlength:
        raise ValueError("STRING TOO LONG")
    return DATA[offset:offset+length].decode("utf8")
def write_string(index: int, string: str):
    global STRING_OFFSETS, DATA
    offset = STRING_OFFSETS[index][1]
    if offset == 0: return
    maxlen = STRING_OFFSETS[index][3]
    encoded = bytearray(string.encode("utf8")) + b"\0"
    while len(encoded) < maxlen:
        encoded += b"\0"
    if len(encoded) != maxlen:
        raise ValueError("STRING TOO LONG")
    DATA[offset:offset+maxlen] = encoded

category_tab("INVENTORY")

category(7+3, 16, "Params", 5)
property_sint(offset=0x0d20, bytes=4, name="Current Sticker Page", min=0, max=17, padding=1)
property_sint(offset=0x0d24, bytes=4, name="Sticker Page Count", min=0, max=18, padding=1)
property_sint(offset=0x0d28, bytes=4, name="Current Scrap Page", min=0, max=8, padding=1)
property_sint(offset=0x0e58, bytes=4, name="Thing count", min=0, max=64, padding=1, tooltip="ammount of things in the thing pages. Empty values cause issues.")

PAGE_SAVE_CALLBACKS: list = []
PAGE_LOAD_CALLBACKS: list = []
current_page: tk.StringVar = tk.StringVar()
current_page_int: int = -1
page_dropdown = ttk.Combobox(CURRENT_TAB_ROOT, textvariable=current_page, width=15, height=20)
page_dropdown.grid(row=0, column=7)
page_dropdown["values"] = ITEM_PAGES
page_dropdown["state"] = "disabled"

def page_init():
    global current_page_int
    page_dropdown["state"] = "normal"
    current_page_int = -1
    page_dropdown.current(1)
    current_page_int = -1
    page_dropdown.current(0)
INIT_CALLBACKS.append(page_init)
def page_changed(a=None,b=None,c=None):
    global current_page_int
    for callback in PAGE_SAVE_CALLBACKS:
        callback()
    current_page_int = page_dropdown.current()
    for callback in PAGE_LOAD_CALLBACKS:
        callback()
CHANGE_CALLBACKS.append(page_changed)

current_page.trace_add("write", page_changed)

def register_item_page_entry(root, row: int, item_index: int):
    selected_item = tk.StringVar(value="[EMPTY]")
    unknown_var = tk.StringVar(value="0")
    x_var = tk.StringVar(value="0")
    y_var = tk.StringVar(value="0")
    item_select = ttk.Combobox(root, textvariable=selected_item, height=32, width=32)
    options = ["[EMPTY]"]
    options.extend([v for v in ITEM_NAMES if v.startswith("SL_") or v.startswith("PK_")])
    item_select["values"] = options
    item_select.grid(row=row, column=7, sticky="w")
    unknown_select = ttk.Spinbox(root, textvariable=unknown_var, from_=0, to=65535, width=6)
    unknown_select.grid(row=row, column=9, sticky="w")
    x_select = ttk.Spinbox(root, textvariable=x_var, width=6, from_=-32768, to=32767)
    x_select.grid(row=row, column=11, sticky="w")
    y_select = ttk.Spinbox(root, textvariable=y_var, width=6, from_=-32768, to=32767)
    y_select.grid(row=row, column=13, sticky="w")
    ttk.Label(root, justify="right", text=" item").grid(row=row, column=6, sticky="e")
    ttk.Label(root, justify="right", text=" unknown").grid(row=row, column=8, sticky="e")
    ttk.Label(root, justify="right", text=" x").grid(row=row, column=10, sticky="e")
    ttk.Label(root, justify="right", text=" y").grid(row=row, column=12, sticky="e")

    def load():
        if current_page_int == -1: return
        offset = ITEM_PAGE_BASE_OFFSET + ITEM_PAGE_SIZE * current_page_int + item_index * 10
        item = read_uint(offset, 2)
        unknown = read_uint(offset + 2, 2)
        item_type = read_uint(offset + 4, 2)
        x = read_int(offset + 6, 2)
        y = read_int(offset + 8, 2)

        if item_type == 16383:
            item = -1
        selected_item.set(ITEM_NAMES[item] if 0 <= item < len(ITEM_NAMES) else "[EMPTY]")
        unknown_var.set(str(unknown))
        x_var.set(str(x))
        y_var.set(str(y))
    def save():
        if current_page_int == -1: return
        offset = ITEM_PAGE_BASE_OFFSET + ITEM_PAGE_SIZE * current_page_int + item_index * 10
        item_name = item_select.get()
        item = ITEM_INDEX_LOOKUP[item_name] if item_name in ITEM_INDEX_LOOKUP else -1
        unknown = int(unknown_var.get()) if unknown_var.get().isascii() and unknown_var.get().isnumeric() else 0
        x = int(x_var.get()) if x_var.get().isascii() and x_var.get().isnumeric() else 0
        y = int(y_var.get()) if y_var.get().isascii() and y_var.get().isnumeric() else 0

        item_type = 0
        if item < 0: # invalid or empty
            item_type = 16383
        else:
            item_type = TEMP_ITEM_TYPES[ITEM_TYPES[ITEM_NAMES[item]]]

        write_uint(offset, item, 2)
        write_uint(offset+2, unknown, 2)
        write_uint(offset+4, item_type, 2)
        write_int(offset+6, x, 2)
        write_int(offset+8, y, 2)

    def init():
        nonlocal x_select, y_select, unknown_select, item_select
        x_select["state"] = "normal"
        y_select["state"] = "normal"
        unknown_select["state"] = "normal"
        item_select["state"] = "normal"
    x_select["state"] = "disabled"
    y_select["state"] = "disabled"
    unknown_select["state"] = "disabled"
    item_select["state"] = "disabled"

    PAGE_SAVE_CALLBACKS.append(save)
    PAGE_LOAD_CALLBACKS.append(load)
    INIT_CALLBACKS.append(init)

for i in range(15):
    register_item_page_entry(CURRENT_TAB_ROOT, 1+i, i)

THING_PAGE_SAVE_CALLBACKS: list = []
THING_PAGE_LOAD_CALLBACKS: list = []
current_thing_page: tk.StringVar = tk.StringVar()
current_thing_page_int: int = -1
thing_page_dropdown = ttk.Combobox(CURRENT_TAB_ROOT, textvariable=current_thing_page, width=15, height=20)
thing_page_dropdown.grid(row=16, column=7)
thing_page_dropdown["values"] = [f"ThingPage{i+1}" for i in range(13)]
thing_page_dropdown["state"] = "disabled"
ttk.Label(CURRENT_TAB_ROOT, text="Things:").grid(row=16, column=6)

def thing_page_init():
    global current_thing_page_int
    thing_page_dropdown["state"] = "normal"
    current_thing_page_int = -1
    thing_page_dropdown.current(1)
    current_thing_page_int = -1
    thing_page_dropdown.current(0)
INIT_CALLBACKS.append(thing_page_init)
def thing_page_changed(a=None,b=None,c=None):
    global current_thing_page_int
    for callback in THING_PAGE_SAVE_CALLBACKS:
        callback()
    current_thing_page_int = thing_page_dropdown.current()
    for callback in THING_PAGE_LOAD_CALLBACKS:
        callback()
CHANGE_CALLBACKS.append(thing_page_changed)

current_thing_page.trace_add("write", thing_page_changed)

THING_BASE_OFFSET = 0x0d58

def register_thing_page_entry(root, row: int, index: int):
    selected_item = tk.StringVar(value="[EMPTY]")
    unknown_var = tk.StringVar(value="0")
    item_select = ttk.Combobox(root, textvariable=selected_item, height=32, width=32)
    options = ["[EMPTY]"]
    options.extend([v for v in ITEM_NAMES if v.startswith("REAL_")])
    item_select["values"] = options
    item_select.grid(row=row, column=7)
    unknown_select = ttk.Spinbox(root, textvariable=unknown_var, from_=0, to=65535, width=6)
    unknown_select.grid(row=row, column=9)
    ttk.Label(root, text="thing").grid(row=row, column=6)
    ttk.Label(root, text="unknown").grid(row=row, column=8)

    def save():
        if current_thing_page_int == -1: return
        if current_thing_page_int == 12 and index == 4: return # do not overwrite thing count
        offset = THING_BASE_OFFSET + (5*4) * current_thing_page_int + index * 4
        item_name = item_select.get()
        item = ITEM_INDEX_LOOKUP[item_name] if item_name in ITEM_INDEX_LOOKUP else -1
        unknown = int(unknown_var.get()) if unknown_var.get().isascii() and unknown_var.get().isnumeric() else 0
        if item < 0:
            write_uint(offset, 0, 2)
            write_uint(offset + 2, 0, 2)
        else:
            write_uint(offset, item, 2)
            write_uint(offset + 2, unknown, 2)

    def load():
        nonlocal init
        if current_thing_page_int == -1: return
        if current_thing_page_int == 12 and index == 4:
            unknown_select["state"] = "disabled"
            item_select["state"] = "disabled"
        else:
            init()
        offset = THING_BASE_OFFSET + (5*4) * current_thing_page_int + index * 4
        item = read_uint(offset, 2)
        unknown = read_uint(offset + 2, 2)
        selected_item.set(ITEM_NAMES[item] if 0 < item < len(ITEM_NAMES) else "[EMPTY]")
        unknown_var.set(str(unknown))


    def init():
        nonlocal unknown_select, item_select
        if current_thing_page_int == 12 and index == 4: return # do not overwrite thing count
        unknown_select["state"] = "normal"
        item_select["state"] = "normal"
    unknown_select["state"] = "disabled"
    item_select["state"] = "disabled"

    THING_PAGE_SAVE_CALLBACKS.append(save)
    THING_PAGE_LOAD_CALLBACKS.append(load)
    INIT_CALLBACKS.append(init)

for i in range(5):
    register_thing_page_entry(CURRENT_TAB_ROOT, 17+i, i)

ttk.Label(CURRENT_TAB_ROOT, text="WARNING: The thing count needs to be adjusted manually at the moment.").grid(row=22, column=6, columnspan=8)
ttk.Label(CURRENT_TAB_ROOT, text="Leaving gaps in the thing list will crash the game if the gap is selected.").grid(row=23, column=6, columnspan=8)
ttk.Label(CURRENT_TAB_ROOT, text="Raising the sticker page count above 8 will make the sticker pages overflow into the scrap pages").grid(row=24, column=6, columnspan=8)

def register_switch_editor(root, name: str, switches: dict[str, int], row: int, tooltip: None|str = None):
    # required variables
    last_switch_name = ""
    last_switch_index = -1
    switch_names = [k for k in switches]
    selected_switch = tk.StringVar()
    switch_value_ref = tk.StringVar()
    switch_dropdown = ttk.Combobox(root, textvariable=selected_switch, width=DROPDOWN_WIDTHS, height=32)
    if TOOLTIPS_ENABLED and tooltip is not None:
        Hovertip(switch_dropdown, tooltip)
    switch_value: ttk.Spinbox = ttk.Spinbox(root, from_=0, to=255, increment=1, textvariable=switch_value_ref, width=4)
    label: ttk.Label = ttk.Label(root, text=name)

    def switch_changed(a=None, b=None, c=None, d=None, e=None):
        nonlocal last_switch_name, switch_value, switch_dropdown, selected_switch, last_switch_index
        switch_index = switch_dropdown.current()
        # uninitialized
        if switch_index == -1: 
            return
        current_value = switch_value.get()
        if last_switch_name != "" and last_switch_name in switches:
            try:
                # this does not catch everything but it does catch a lot
                if current_value.isnumeric():
                    write_uint(switches[last_switch_name], int(current_value), 1)
            except e:
                print("an error occurred while writing the value")
                raise

        switch_names[last_switch_index] = f"{last_switch_name}: {current_value}"

        # update value reference
        last_switch_index = switch_index
        last_switch_name = selected_switch.get().split(":")[0]
        if last_switch_name in switches:
            switch_value_ref.set(str(read_uint(switches[last_switch_name], 1)))
        else:
            switch_value_ref.set("-1")
        if selected_switch.get().__contains__(":"):
            selected_switch.set(last_switch_name)
        switch_names[last_switch_index] = f"{last_switch_name}"
        switch_dropdown['values'] = switch_names
    
    def init():
        nonlocal switch_dropdown, switch_value, switch_names
        switch_dropdown['state'] = 'normal'
        switch_value['state'] = 'normal'
        switch_names = [f"{k}: {read_uint(switches[k], 1)}" for k in switches.keys()]
        switch_dropdown['values'] = switch_names
    
    CHANGE_CALLBACKS.append(switch_changed)
    INIT_CALLBACKS.append(init)

    # set up ui elements
    label.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=6, columnspan=1)
    selected_switch.trace_add("write", switch_changed)
    switch_dropdown['values'] = switch_names
    switch_dropdown.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=7, columnspan=2)
    switch_dropdown['state'] = 'disabled'
    switch_value.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=9, columnspan=3)
    switch_value['state'] = 'disabled'

def register_flag_editor(root, name: str, flags: dict[str, tuple[int, int]], row: int, tooltip: None|str = None):
    last_flag_name = ""
    last_flag_index = -1
    flag_names = [k for k in flags.keys()]

    label: ttk.Label = ttk.Label(root, text=name)
    selected_flag = tk.StringVar()
    flag_dropdown = ttk.Combobox(root, textvariable=selected_flag, width=DROPDOWN_WIDTHS, height=32)
    if TOOLTIPS_ENABLED and tooltip is not None:
        Hovertip(flag_dropdown, tooltip)
    flag_value = tk.BooleanVar()
    flag_button = ttk.Checkbutton(root, text="", variable=flag_value)

    def flag_changed(a=None, b=None, c=None, d=None, e=None):
        nonlocal last_flag_name, last_flag_index, flag_dropdown
        flag_index = flag_dropdown.current()
        if flag_index == -1: 
            # invalid value
            return
        current_value = flag_value.get()
        if last_flag_name != "" and last_flag_name in flags:
            write_bool(flags[last_flag_name][0], flags[last_flag_name][1], current_value)

        flag_names[last_flag_index] = f"{last_flag_name}: {current_value}" # f"{last_flag_name}:[{current_value}]"

        last_flag_index = flag_index
        last_flag_name = selected_flag.get().split(":")[0].split("[")[0]
        if last_flag_name in flags:
            flag_value.set(read_bool(flags[last_flag_name][0], flags[last_flag_name][1]))
        if selected_flag.get().__contains__(":"):
            selected_flag.set(last_flag_name)

        flag_names[last_flag_index] = f"{last_flag_name}"
        flag_dropdown['values'] = flag_names

    def init():
        nonlocal flag_dropdown, flag_button, flag_names
        flag_dropdown['state'] = 'normal'
        flag_button['state'] = 'normal'
        #flag_names = [f"{k}:[{read_bool(flags[k][0], flags[k][1])}]" for k in flags.keys()]
        flag_names = [f"{k}: {read_bool(flags[k][0], flags[k][1])}" for k in flags.keys()]
        flag_dropdown['values'] = flag_names
    
    CHANGE_CALLBACKS.append(flag_changed)
    INIT_CALLBACKS.append(init)

    # init ui elements
    label.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=6, columnspan=1)
    selected_flag.trace_add("write", flag_changed)
    flag_dropdown['values'] = flag_names
    flag_dropdown.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=7, columnspan=2)
    flag_dropdown['state'] = 'disabled'
    flag_button.grid(row=row+FLAG_SWITCH_ROW_START, rowspan=1, column=9, columnspan=3)
    flag_button['state'] = 'disabled'

category_tab("GENERAL", 0)

# includes its own category label
property_date()
category(2, 1, "Playtime")
property_uint(offset=0x001c, bytes=1, name="Seconds")
property_uint(offset=0x001e, bytes=1, name="Minutes")
property_uint(offset=0x001f, bytes=1, name="Hours")

category(4, 1, "Mario Stats")
property_sint(offset=0x014c, bytes=4, name="Health", min=1, max=100)
property_sint(offset=0x0150, bytes=4, name="Max Health", min=1, max=100)
property_sint(offset=0x017c, bytes=4, name="Comet pieces", min=0, max=38, tooltip="value displayed in album")
property_sint(offset=0x0148, bytes=4, name="Coin count", min=0, max=9999)

category(2, 5, "Abilities")
property_bool(offset=0x0184, index=0, name="has hammer", tooltip="can use the hammer in the overworld and in battle")
property_bool(offset=0x0184, index=2, name="has kersti", tooltip="can talk to kersti, paperize and use the battle spinner (if unlocked)")

achievement_list: list[tuple[int, int, str, int, int, str]] = [
    (0x0e80, 0x0ea4, "comet pieces collected", 0, 38, None),
    (0x0e84, 0x0ea8, "secret doors used", 0, 35, None),
    (0x0e88, 0x0eac, "sticker collection progress", 0, 160, None),
    (0x0e8c, 0x0eb0, "hp plus health", 20, 100, None),
    (0x0e90, 0x0eb4, "coins spent in shops", 0, 10000, None),
    (0x0e94, 0x0eb8, "battles with perfect", 0, 500, None),
    (0x0e98, 0x0ebc, "unknown", None, None, None),
    (0x0e9c, 0x0ec0, "excellent attack count", 0, 1000, None),
    (0x0ea0, 0x0ec4, "battle spinner jackpot", 0, 50, None),
]
category(0, 10, "achievement progress")
for value_offset, target_offset, name, min, max, tooltip in achievement_list:
    property_sint(value_offset, 4, name, tooltip, min, max)
category(2, 10, "progress target", None, 1) # achievement progression target
for value_offset, target_offset, name, min, max, tooltip in achievement_list:
    property_sint(target_offset, 4, None, tooltip, min, max)

category(3, 10, "Royal stickers", tooltip="Visual representation of collected royal stickers")
for i in range(6): property_bool(offset=0x0020, index=i, name=f"SaveMenu{i+1}", thin=True, tooltip="display in save select")
category(4, 10, "") # (royal stickers in game)
for i in range(6): property_bool(offset=0x0180, index=i, name=f"OnAlbum{i+1}", thin=True, tooltip="display on album cover")


category_tab("FLAGS/SWITCHES")
FLAG_SWITCH_ROW_START = 0
register_flag_editor(CURRENT_TAB_ROOT, "Global Flags", FLAG_OFFSETS, 1, tooltip="story progression booleans")
register_switch_editor(CURRENT_TAB_ROOT, "Global Switches", SWITCH_OFFSETS, 2, tooltip="story progression integers")
register_flag_editor(CURRENT_TAB_ROOT, "Global mapobject Flags", MOBJ_FLAG_OFFSETS, 3, tooltip="map object interactions")
register_switch_editor(CURRENT_TAB_ROOT, "Global mapobject Switches", MOBJ_SWITCH_OFFSETS, 4, tooltip="map object interactions")
register_flag_editor(CURRENT_TAB_ROOT, "Global item flags", ITEM_FLAG_OFFSETS, 5, "picked up stickers")
register_flag_editor(CURRENT_TAB_ROOT, "Temporary (a) Flags", AF_OFFSETS, 6, "reset when mario exits to the world map")
register_switch_editor(CURRENT_TAB_ROOT, "Temporary (a) Switches", AS_OFFSETS, 7, "reset when mario exits to the world map")
register_flag_editor(CURRENT_TAB_ROOT, "Temporary (a) mapobject Flags", A_MOBJ_FLAG_OFFSETS, 8, "reset when mario exits to the world map")
register_switch_editor(CURRENT_TAB_ROOT, "Temporary (a) mapobject Switches", A_MOBJ_SWITCH_OFFSETS, 9, "reset when mario exits to the world map")
register_flag_editor(CURRENT_TAB_ROOT, "Temporary (a) item flags", A_ITEM_FLAG_OFFSETS, 10, "reset when mario exits to the world map")
# not sure whether those are flags or switches
register_flag_editor(CURRENT_TAB_ROOT, "Global Itemlist flags", ITEM2_FLAG_OFFSETS, 11, "unknown purpose, tracks when mario peels of some stickers or hits some blocks")
register_switch_editor(CURRENT_TAB_ROOT, "Temporary (a) itemlist switches", A_ITEM2_SWITCH_OFFSETS, 12, "most likely used to track how often mario has already hit a block")
#ttk.Label(CURRENT_TAB_ROOT, text="").grid(row=FLAG_SWITCH_ROW_START+13, column=6, columnspan=2)
#register_switch_editor(CURRENT_TAB_ROOT, "ilist_s", ITEM2_SWITCH_OFFSETS, 13) # NOTE: these are empty
#register_flag_editor(CURRENT_TAB_ROOT, "ilist_af", A_ITEM2_FLAG_OFFSETS, 14) # NOTE: these are empty
save_flag_description = scrolledtext.ScrolledText(CURRENT_TAB_ROOT)
save_flag_description.grid(row=14, column=0, columnspan=16, sticky="ew")
save_flag_description.insert("end", """NOTE: Some switches may be 16 or 32 bits in size. These are not properly implemented yet.

Known Flags
===========

World Map
---------
gf_wm_[A]_[B]  - connection from level A to level B unlocked
gf_wm_icon_[A] - show icon for level A
gf_wm_hana_[A] - show wiggler piece icon at level A

Abilities
---------
gf_tutorial_pepalyze          - unlock paperize ability
gf_tutorial_first_roulette_00 - unlock battle spinner
gf_pouch_get_sealbook         - unlock sticker album
gf_pouch_get_mappiece         - unlock album scrap section
gf_pouch_get_monoart          - unlock album thing section

Other
-----
gf_museum_[A]_seal_[B] - donated sticker type A (robj/btl) number B to the museum
gf_*_talk_* - has heared specific dialog and can skip it
every paperization has a flag which marks whether it has been completed yet

Other Dropdowns
===============
Global switches are similar to global flags but they store an 8-bit number instead.
Global mapobject Flags are like Global Flags but tied to a specific object in the world.
Global mapobject Switches: like mapobject flags
Global item flags: Some stickers can only be collected once. This tracks their collection


The temporary sections are like the global sections but are cleared every time mario 
returns to the world map. 
Those the flags and switches referenced in the asSwitchTable and afSwitchTable.
""")
save_flag_description["state"] = "disabled"

category_tab("MAP STRINGS")
#category(0, 23, "map strings")
STRINGREFS: list[tuple[ttk.Combobox, tk.StringVar]] = []
for i, (vtype, offset, name, maxlength, tooltip) in enumerate(STRING_OFFSETS):
    string_label = ttk.Label(CURRENT_TAB_ROOT, text=name)
    string_label.grid(row=i+CURRENT_ROW, column=0)
    current_string = tk.StringVar()
    string_dropdown = ttk.Combobox(CURRENT_TAB_ROOT, textvariable=current_string, width=32)
    if TOOLTIPS_ENABLED:
        Hovertip(string_dropdown, tooltip)
    string_dropdown.grid(row=i+CURRENT_ROW, column=1, columnspan=2)
    if vtype == STRING_TYPE_LEVEL_REF_SELECT:
        levels = ["WLD"]
        for m in MAP_NAME_LIST: levels.append(m)
        string_dropdown['values'] = levels
    elif vtype == STRING_TYPE_LEVEL_REF:
        string_dropdown['values'] = MAP_NAME_LIST
    elif vtype == STRING_TYPE_MAP_REF:
        mapname = STRINGREFS[4][1].get()
        if mapname in MAP_NAMES:
            string_dropdown["values"] = MAP_NAMES[mapname]
        #elif mapname != "WLD":
        #    string_dropdown["values"] = ["ERROR"]
        else:
            string_dropdown["values"] = ["wld"]
    elif vtype == STRING_TYPE_ENTRANCE_REF:
        current_room = STRINGREFS[5][1].get()
        if current_room in ENTRANCE_NAMES:
            string_dropdown["values"] = ENTRANCE_NAMES[current_room]
        else:
            string_dropdown["values"] = ["ERROR"]
    elif vtype == STRING_TYPE_BATTLE_REF:
        string_dropdown["values"] = ENCOUNTER_NAME_LIST
    else:
        continue
    string_dropdown.current(0)
    string_dropdown['state'] = 'disabled'
    STRINGREFS.append((string_dropdown, current_string))
STRINGREFS[4][1].trace_add("write", on_level_changed)
STRINGREFS[5][1].trace_add("write", on_map_changed)

# experimental (does not work)
def add_theming():
    style = ttk.Style(root)
    def change_theme(a=None,b=None):
        #print(a,b)
        if theme_box.current() != -1:
            style.theme_use(theme_box.get())
        return True
    theme_box = ttk.Combobox(file_controls, validate="all", postcommand=change_theme, validatecommand=change_theme, xscrollcommand=change_theme)
    theme_box["values"] = [name for name in style.theme_names()]
    theme_box.set("default")
    theme_box.grid(row=0, column=3, columnspan=2)
    ttk.Label(file_controls, text="UI Theme").grid(row=0, column=2)
#add_theming() # this does not do anything useful but may be useful in the future

if len(sys.argv) > 1 and sys.argv[1].endswith(".bin") and os.path.isfile(sys.argv[1]): 
    load_data(sys.argv[1])
else: load_path()

root.mainloop()
