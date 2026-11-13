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

# NOTE: Setting the inventory items to values of the wrong type will likely crash the game

# config
CHECK_LIMITS: bool = False

# constants
SAVEEDIT_VERSION = "0.2.0"

SAVE_GS_START = 0x1a04
SAVE_GF_START = 0x1b44
SAVE_AS_START = 0x1d04
SAVE_AF_START = 0x1e04
ITEM_PAGE_BASE_OFFSET: int = 0x01e0
ITEM_PAGE_ITEM_COUNT: int = 15
ITEM_PAGE_SIZE: int = 160
THING_BASE_OFFSET = 0x0d58
THING_TOTAL_COUNT = 64

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

MAP_NPC_IDS: dict[str, dict[str,tuple[str,int]]] = {}

PAPERIZE_MUSEUM_CHECK_NAMES = ["[DUMMY]"]
PAPERIZE_CHECK_NAMES = ["[DUMMY]"]

THING_UNLOCK_ORDER: dict[str, tuple[int, int]] = {}

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
    if DATAPATH == () or DATAPATH == "" or DATAPATH is None:
        exit(1)

    # link data
    LINK_DATA = kdm.load(f"{DATAPATH}/kdm_link_data.bin")
    for area in LINK_DATA["link_data_all"]:
        area = area[0]
        ENTRANCE_NAMES[area["Name"]] = []
        for link in area["Links"]:
            link = link[0]
            ENTRANCE_NAMES[area["Name"]].append(link["FromDoor"])
    
    WORLDMAP_DATA = kdm.load(f"{DATAPATH}/kdm_mapdata.bin")
    for area in WORLDMAP_DATA["mapDataTable"]:
        area = area[0]
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
    for i, item in enumerate(ITEMS["ItemDataSaveList"]):
        item = item[0]
        ITEM_NAMES.append(item["Name"])
        ITEM_INDEX_LOOKUP[item["Name"]] = i
        ITEM_TYPES[item["Name"]] = item["ItemVariant"]["VariantTypeEnum"]
        if item["ItemVariant"]["VariantTypeEnum"] == 2:
            offset = item["ItemVariant"]["VariantValue"][0]["Unknown_Int_3"]
            THING_UNLOCK_ORDER[item["Name"]] = (0x0e60 + offset // 8, offset % 8)
    for i in range(8):
        ITEM_PAGES.append(f"StickerPage{i+1}")
    for i in range(9):
        ITEM_PAGES.append(f"ScrapPage{i+1}")
    for i in range(1):
        ITEM_PAGES.append(f"Unknown{i}")

    # flags
    flaginfo = kdm.load(f"{DATAPATH}/kdm_switch.bin")
    for flag in flaginfo["gfSwitchTable"]:
        if flag["Name"].__contains__("_mobj_item_"): continue # dummy?
        FLAG_OFFSETS[flag["Name"]] = (SAVE_GF_START + flag["Offset"] // 8, flag["Offset"] % 8)
    for switch in flaginfo["gsSwitchTable"]:
        if switch["Name"].__contains__("_mobj_item_"): 
            continue # dummy?
        SWITCH_OFFSETS[switch["Name"]] = SAVE_GS_START + switch["Offset"]
    for switch in flaginfo["asSwitchTable"]:
        if switch["Name"].__contains__("_mobj_item_"): 
            continue # dummy?
        AS_OFFSETS[switch["Name"]] = SAVE_AS_START + switch["Offset"]
    # NOTE: THESE ARE MAP SPECIFIC
    for flag in flaginfo["afSwitchTable"]:
        if flag["Name"].__contains__("_mobj_item_"): continue # dummy?
        AF_OFFSETS[flag["Name"]] = (SAVE_AF_START + flag["Offset"] // 8, flag["Offset"] % 8)
    
    disposdata = kdm.load(f"{DATAPATH}/kdm_dispos_data.bin")
    for level in disposdata["all_disposDataTbl"]:
        if level is None: break # null terminator
        level = level[0]
        if level["Name"] in ["CHECK", "TST"]: continue # debugging levels
        for encounter in level["Encounters"]:
            if encounter is None: break # null terminator
            encounter = encounter[0]
            ENCOUNTER_NAME_LIST.append(encounter["Elements"][0]["Name"])

        for area in level["NPCs"]:
            area = area[0]
            MAP_NPC_IDS[area["Map"]] = {}
            for npc in area["NPCs"]:
                MAP_NPC_IDS[area["Map"]][npc["Name"]] = (npc["AssociatedEncounter"][0]["Name"] if npc["AssociatedEncounter"] is not None else "", npc["EncounterID"])
        for area in level["MapObjects"]:
            if area is None: break # null terminator
            area = area[0]
            for obj in area["MapObjects"]:
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
        for area in level["MapItems"]:
            if area is None: break # null terminator
            area = area[0]
            for item in area["Items"]:
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
                    typelist = item["TypeList"][0]
                    offset1 = typelist["SwitchOffset"]
                    if offset1 < 10000: # gs?
                        ITEM2_SWITCH_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = SAVE_GS_START + offset1
                    else:
                        offset1 = offset1 % 10000
                        A_ITEM2_SWITCH_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = SAVE_AS_START + offset1
                    offset2 = typelist["FlagOffset"]
                    if offset2 < 10000: # gf?
                        ITEM2_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = (SAVE_GF_START + offset2 // 8, offset2 % 8)
                    else:
                        offset2 = offset2 % 10000
                        A_ITEM2_FLAG_OFFSETS[f'{level["Name"]} {area["MapName"]} {typelist["Name"]}'] = (SAVE_AF_START + offset2 // 8, offset2 % 8)
    pepa_data = kdm.load(f"{DATAPATH}/kdm_pepalyze.bin")
    for lock in pepa_data["lockDataTable"]:
        lock = lock[0]
        if len(PAPERIZE_CHECK_NAMES) != lock["ID"]:
            raise ValueError("paperize data not ID aligned")
        PAPERIZE_CHECK_NAMES.append(lock["Name"])
    pepa_data_m = kdm.load(f"{DATAPATH}/kdm_pepalyze_museum.bin")
    for lock in pepa_data_m["lockDataTable"]:
        lock = lock[0]
        if len(PAPERIZE_MUSEUM_CHECK_NAMES) != lock["ID"]:
            raise ValueError("paperize museum data not ID aligned")
        PAPERIZE_MUSEUM_CHECK_NAMES.append(lock["Name"])

GLOBAL_NAMES: list[str] = ["SAVEEDIT_VERSION", "ENCOUNTER_NAME_LIST", "ITEM_PAGES", 
"ITEM_NAMES", "ITEM_INDEX_LOOKUP", "ITEM_TYPES", "FLAG_OFFSETS", "SWITCH_OFFSETS", 
"MOBJ_FLAG_OFFSETS", "MOBJ_SWITCH_OFFSETS", "ITEM_FLAG_OFFSETS", "ITEM2_SWITCH_OFFSETS", 
"ITEM2_FLAG_OFFSETS", "AS_OFFSETS", "AF_OFFSETS", "A_MOBJ_FLAG_OFFSETS", "A_MOBJ_SWITCH_OFFSETS", 
"A_ITEM_FLAG_OFFSETS", "A_ITEM2_SWITCH_OFFSETS", "A_ITEM2_FLAG_OFFSETS", "MAP_NAME_LIST", 
"MAP_NPC_IDS", "MAP_NAMES", "ENTRANCE_NAMES", "PAPERIZE_MUSEUM_CHECK_NAMES", "PAPERIZE_CHECK_NAMES",
"THING_UNLOCK_ORDER"]
CONSTANT_JSON_PATH = __file__.replace(".py", "_constants.json")
def init_options_pregenerated():
    import json
    with open(CONSTANT_JSON_PATH, "r") as f: 
        constants = json.load(f)
    if SAVEEDIT_VERSION is not None and ("SAVEEDIT_VERSION" not in constants or constants["SAVEEDIT_VERSION"] != SAVEEDIT_VERSION):
        result = messagebox.showerror("incorrect saveedit_constants.json version", "The version of the constants json file does not match. Please redownload it or select the data directory of a sticker star rom dump to regenerate it now.", type=messagebox.OKCANCEL)
        if result != "ok":
            quit(1)
        init_options()
        dump_constants()
        return
    globals_dict = globals()
    for g in GLOBAL_NAMES:
        if g in constants:
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
 
# initialize with zeroes so nothing breaks until a file is loaded
DATA = bytearray(0x26b0)

# cache results instead of parsing all files every time
# TODO: display info popup if json file is missing
if (len(sys.argv) > 1 and sys.argv[1] == "dumpconstants"): 
    init_options()
    dump_constants()
elif (len(sys.argv) > 1 and sys.argv[1] == "noconstants"): 
    init_options()
elif not os.path.isfile(CONSTANT_JSON_PATH):
    result = messagebox.showerror("missing saveedit_constants.json", "Can not find constants json file. Please download it or select the data directory of a sticker star rom dump to generate it now.", type=messagebox.OKCANCEL)
    if result != "ok":
        quit(1)
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
    global DATA, OPENED_PATH
    if filename is not None and filename != () and filename != "":
        with open(filename, "rb") as f:
            d = f.read()
            if len(d) != 0x26b0:
                messagebox.showwarning("invalid save file", "file length does not match")
                return
            elif d[0:8] != b"\xF6\x04\x33\x01\x14\x07\x00\x00":
                messagebox.showwarning("invalid save file", "invalid file header")
                return
            DATA = bytearray(d)
    else:
        return
    if len(DATA) == 0:
        return
    OPENED_PATH = filename
    menubar.entryconfigure(2, state="normal")
    for callback in INIT_CALLBACKS:
        callback()

def save_path():
    global DATA, OPENED_PATH
    path_parts = OPENED_PATH.replace("\\", "/").split("/")
    # ensure all data has been saved
    for callback in CHANGE_CALLBACKS:
        callback()
    # save file
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

# temp, count uneditable bytes
def file_debug():
    t = []
    for b in DATA:
        if b not in t: t.append(b)
    for i in range(257):
        if i not in t: break
    if i == 256: 
        print("CAN NOT TEST")
        return
    for j in range(len(DATA)): DATA[j] = i if not (0x0ef4 <= j < 0x11f8 + 2048) and not (0x1a04 <= j < 0x1fc8) else 0
    for c in CHANGE_CALLBACKS: c()
    t = 0
    for j, b in enumerate(DATA): t += b == i
    print(f"{t}/{len(DATA)} bytes left unknown ({t/len(DATA)*100:.4}%)")

menubar = tk.Menu(root)
menubar.add_command(label="load", command=load_path)
menubar.add_command(label="save", command=save_path, state="disabled")
#menubar.add_command(label="count unknown bytes", command=file_debug)
root.config(menu=menubar)

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
def property_sint_enum(offset: int, bytes: int, name: str, keyvalues: dict[str, int], tooltip: None|str=None):
    global CURRENT_TAB_ROOT, CURRENT_COL, CURRENT_ROW
    c = CURRENT_COL
    if name is not None and name != "":
        ttk.Label(CURRENT_TAB_ROOT, text=name).grid(row=CURRENT_ROW, column=c)
        c += 1
    keys = [k for k in keyvalues.keys()]

    value = tk.StringVar()
    dropdown = ttk.Combobox(CURRENT_TAB_ROOT, values=keys, textvariable=value, width=11)
    dropdown.grid(row=CURRENT_ROW, column=c)

    if TOOLTIPS_ENABLED and tooltip is not None:
        Hovertip(dropdown, tooltip)
    dropdown["state"] = "disabled"

    def save(): 
        v = value.get()
        if v in keyvalues:
            write_int(offset, keyvalues[v], bytes)
    def load():
        nonlocal dropdown
        dropdown["state"] = "normal"
        v = read_int(offset, bytes)
        value.set("")
        for k in keyvalues:
            if keyvalues[k] == v: value.set(k)
        #if value.get() == "": print(v)
    CHANGE_CALLBACKS.append(save)
    INIT_CALLBACKS.append(load)
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
    STRINGREFS[5][0]["values"] = MAP_NAMES[level] if level in MAP_NAMES else ["wld" if level == "WLD" else ""]
    if STRINGREFS[5][0].current() == -1: STRINGREFS[5][0].current(0)
def on_map_changed(index, value, op):
    global STRINGREFS
    current_room = STRINGREFS[5][1].get()
    if current_room in ENTRANCE_NAMES:
        STRINGREFS[6][0]["values"] = ENTRANCE_NAMES[current_room]
    #elif current_room != "wld":
    #    STRINGREFS[6][0]["values"] = ["ERROR"]
    else:
        STRINGREFS[6][0]["values"] = [""]
    STRINGREFS[6][0].current(0)

def load_strings():
    for i, ref in enumerate(STRINGREFS):
        STRINGREFS[i][0]['state'] = 'normal'
        s = read_string(i)
        if i < 4:
            s = s.upper()
        STRINGREFS[i][0].set(s)
    if STRINGREFS[5][0].get() == "wld":
        STRINGREFS[4][0].set("WLD")
        STRINGREFS[6][0].set("") # clear level enter function name on world
    else:
        STRINGREFS[4][0].set(STRINGREFS[3][0].get())
def save_strings():
    for i, ref in enumerate(STRINGREFS):
        write_string(i, STRINGREFS[i][0].get())
    # player saved on world map insted of in level
    write_bool(0x0144, 0, STRINGREFS[5][0].get() == "wld")
INIT_CALLBACKS.append(load_strings)
CHANGE_CALLBACKS.append(save_strings)

# TODO: decouple from STRING_OFFSETS
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

inventory_tree_columns = ("sticker", "unknown", "x", "y")
inventory_tree_frame = tk.Frame(CURRENT_TAB_ROOT)
inventory_tree = ttk.Treeview(inventory_tree_frame, columns=inventory_tree_columns)#, height=26)
inventory_tree.heading("#0", text="page")
inventory_tree.column("#0", width=96, stretch=False)
inventory_tree.heading("sticker", text="sticker")
inventory_tree.heading("unknown", text="unknown")
inventory_tree.column("unknown", width=64, stretch=False)
inventory_tree.heading("x", text="x")
inventory_tree.column("x", width=64, stretch=False)
inventory_tree.heading("y", text="y")
inventory_tree.column("y", width=64, stretch=False)

inventory_tree_v_scrollbar = ttk.Scrollbar(inventory_tree_frame, orient=tk.VERTICAL, command=inventory_tree.yview)
inventory_tree.configure(yscrollcommand=inventory_tree_v_scrollbar.set)

inventory_tree.pack(side="left", fill="both", expand=True)
inventory_tree_v_scrollbar.pack(side="right", fill="y")
inventory_tree_frame.pack(fill="both",expand=True)

ITEM_NAMES_INCLUDING_EMPTY = ["[EMPTY]"]
ITEM_NAMES_INCLUDING_EMPTY.extend(ITEM_NAMES)
STICKER_NAMES_INCLUDING_EMPTY = ["[EMPTY]"]
STICKER_NAMES_INCLUDING_EMPTY.extend([n for n in ITEM_NAMES if not CHECK_LIMITS or n.startswith("PK_") or n.startswith("SL_")])
THING_NAMES_INCLUDING_EMPTY = ["[EMPTY]"]
THING_NAMES_INCLUDING_EMPTY.extend([n for n in ITEM_NAMES if not CHECK_LIMITS or n.startswith("REAL_")])

INVENTORY_CLEANUP_FN = None
def inventory_tree_edit_cell(event):
    global INVENTORY_CLEANUP_FN
    item = inventory_tree.identify_row(event.y)
    column = inventory_tree.identify_column(event.x)
    if not item or not column:
        return
    elif column == "#0": 
        # only allow to edit value columns, not the main column
        return
    index = int(column[1:]) - 1
    x, y, width, height = inventory_tree.bbox(item, column)

    if len(inventory_tree.item(item, "values")) <= index: return
    value = inventory_tree.item(item, "values")[index]
    if index == 0:
        item_names = STICKER_NAMES_INCLUDING_EMPTY
        if len(inventory_tree.item(item, "values")) == 2:
            item_names = THING_NAMES_INCLUDING_EMPTY
        entry = ttk.Combobox(inventory_tree, values=item_names)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, inventory_tree.item(item, "values")[index])
        entry.select_range(0, "end")
        #entry["state"] = "readonly"
        entry.focus()
    else:
        int_range = SIGNED_INT_RANGES[2] # if index != 1 else UNSIGNED_INT_RANGES[2]
        entry = ttk.Spinbox(inventory_tree, increment=1, from_=int_range[0], to=int_range[1])
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, inventory_tree.item(item, "values")[index])
        entry.select_range(0, "end")
        entry.focus()

    def save(event=None):
        global INVENTORY_CLEANUP_FN
        INVENTORY_CLEANUP_FN = None
        values = list(inventory_tree.item(item, "values"))
        values[index] = entry.get()
        inventory_tree.item(item, values=values)
        inventory_tree.focus()
        entry.destroy()

    entry.bind("<Return>", save)
    if index != 0: entry.bind("<FocusOut>" if index != 0 else "<<ComboboxSelected>>", save)
    entry.bind("<Escape>", lambda e: entry.destroy())
    INVENTORY_CLEANUP_FN = save

inventory_tree.bind("<1>", lambda e: INVENTORY_CLEANUP_FN() if INVENTORY_CLEANUP_FN else None)
inventory_tree.bind("<Double-1>", inventory_tree_edit_cell)

inventory_items = {}
inventory_things = {}

def inventory_load():
    for offset in inventory_items:
        item = inventory_items[offset]
        item_id = read_int(offset + 0, 2)
        unknown = read_int(offset + 2, 2)
        item_type = read_uint(offset + 4, 2)
        item_pos_x = read_int(offset + 6, 2)
        item_pos_y = read_int(offset + 8, 2)

        item_name = "[EMPTY]"
        if item_type != 16383:
            item_name = ITEM_NAMES[item_id]

        inventory_tree.item(item, values=(item_name, str(unknown), str(item_pos_x), str(item_pos_y)))
    for offset in inventory_things:
        item = inventory_things[offset]
        item_id = read_int(offset + 0, 2)
        unknown = read_int(offset + 2, 2)

        item_name = "[EMPTY]"
        if 0 < item_id < len(ITEM_NAMES):
            item_name = ITEM_NAMES[item_id]

        inventory_tree.item(item, values=(item_name, str(unknown)))

def inventory_save():
    for offset in inventory_items:
        item = inventory_items[offset]
        values = inventory_tree.item(item, "values")
        item_name, unknown, item_pos_x, item_pos_y = values
        if unknown.removeprefix("-").isnumeric() and unknown.removeprefix("-").isascii():
            unknown = int(unknown)
        else: 
            continue
        if item_pos_x.removeprefix("-").isnumeric() and item_pos_x.removeprefix("-").isascii():
            item_pos_x = int(item_pos_x)
        else: 
            continue
        if item_pos_y.removeprefix("-").isnumeric() and item_pos_y.removeprefix("-").isascii():
            item_pos_y = int(item_pos_y)
        else: 
            continue
        
        # invalid item names equal to empty slots
        item_type = (65534 if ITEM_TYPES[item_name] == 3 else 0) if item_name in ITEM_TYPES else 16383
        item_id = ITEM_INDEX_LOOKUP[item_name] if item_name != "[EMPTY]" and item_name in ITEM_INDEX_LOOKUP else 0

        write_int(offset + 0, item_id, 2)
        write_int(offset + 2, unknown, 2)
        write_uint(offset + 4, item_type, 2)
        write_int(offset + 6, item_pos_x, 2)
        write_int(offset + 8, item_pos_y, 2)
    for offset in inventory_things:
        item = inventory_things[offset]
        values = inventory_tree.item(item, "values")
        item_name, unknown = values
        if unknown.removeprefix("-").isnumeric() and unknown.removeprefix("-").isascii():
            unknown = int(unknown)
        else: 
            continue
        item_id = ITEM_INDEX_LOOKUP[item_name] if item_name != "[EMPTY]" and item_name in ITEM_INDEX_LOOKUP else 0
        write_int(offset + 0, item_id, 2)
        write_int(offset + 2, unknown, 2)

INIT_CALLBACKS.append(inventory_load)
CHANGE_CALLBACKS.append(inventory_save)

def register_item_page(name: str, offset: int):
    subtreeroot = inventory_tree.insert("", "end", text=name)
    for i in range(ITEM_PAGE_ITEM_COUNT):
        item_offset = offset + i * 10
        flag_item = inventory_tree.insert(subtreeroot, "end", text="", values=("[EMPTY]", "0", "0", "0"))
        inventory_items[item_offset] = flag_item

for i, page in enumerate(ITEM_PAGES): 
    register_item_page(page, ITEM_PAGE_BASE_OFFSET + i * ITEM_PAGE_SIZE)

temp_thing_page = None
for i in range(THING_TOTAL_COUNT):
    if i % 5 == 0: # 5 things per page
        temp_thing_page = inventory_tree.insert("", "end", text=f"ThingPage{i//5+1}")
    thing_offset = THING_BASE_OFFSET + i * 4
    thing_item = inventory_tree.insert(temp_thing_page, "end", text="", values=("[EMPTY]", "0"))
    inventory_things[thing_offset] = thing_item

# TODO: move inventory parameters back to this page

ttk.Label(CURRENT_TAB_ROOT, text="NOTE: The thing count needs to be adjusted manually on the general page at the moment.").pack()
ttk.Label(CURRENT_TAB_ROOT, text="Leaving gaps in the thing list will crash the game if the gap is selected.").pack()
ttk.Label(CURRENT_TAB_ROOT, text="Raising the sticker page count above 8 will make the sticker pages overflow into the scrap pages").pack()

category_tab("GENERAL", 0)

# includes its own category label
property_date()
category(2, 1, "Playtime")
property_uint(offset=0x001c, bytes=1, name="Seconds")
property_uint(offset=0x001e, bytes=1, name="Minutes")
property_uint(offset=0x001f, bytes=1, name="Hours")

category(4, 6, "TEMP")
property_uint(offset=0x0030, bytes=4, name="Reload Count", tooltip="Highest reload count is the default selected save in save selection")
property_uint(offset=0x0170, bytes=4, name="Escape Chance", tooltip="Percent Chance to escape the next battle.")

category(4, 1, "Mario Stats")
property_sint(offset=0x014c, bytes=4, name="Health", min=1, max=100)
property_sint(offset=0x0150, bytes=4, name="Max Health", min=1, max=100)
property_sint(offset=0x017c, bytes=4, name="Comet pieces", min=0, max=38, tooltip="value displayed in album")
property_sint(offset=0x0148, bytes=4, name="Coin count", min=0, max=9999)

category(2, 5, "Abilities")
property_bool(offset=0x0184, index=0, name="has hammer", tooltip="can use the hammer in the overworld and in battle")
#property_bool(offset=0x0184, index=1, name="unknown", tooltip="never referenced, always available")
property_bool(offset=0x0184, index=2, name="has kersti", tooltip="can talk to kersti, paperize and use the battle spinner (if unlocked)")

category(0, 23, "Sticker Album")
property_sint(offset=0x0d20, bytes=4, name="Current Sticker Page", min=0, max=17)
property_sint(offset=0x0d24, bytes=4, name="Sticker Page Count", min=0, max=18)
property_sint(offset=0x0d28, bytes=4, name="Current Scrap Page", min=0, max=8)
# TODO: calculate this based on the thing list itself
property_sint(offset=0x0e58, bytes=4, name="Thing count", min=0, max=64, tooltip="ammount of things in the thing pages. Empty values cause issues.")

achievement_list: list[tuple[int, int, str, int, int, str]] = [
    (0x0e80, "comet pieces collected", 0, 38, None),
    (0x0e84, "secret doors used", 0, 35, None),
    (0x0e88, "sticker collection progress", 0, 160, None),
    (0x0e8c, "hp plus health", 20, 100, None),
    (0x0e90, "coins spent in shops", 0, 10000, None),
    (0x0e94, "battles with perfect", 0, 500, None),
    (0x0e98, "unknown", None, None, None),
    (0x0e9c, "excellent attack count", 0, 1000, None),
    (0x0ea0, "battle spinner jackpot", 0, 50, None),
]
category(0, 10, "achievement progress")
for value_offset, name, min, max, tooltip in achievement_list:
    property_sint(value_offset, 4, name, tooltip, min, max)
category(2, 10, "progress target", None, 1) # achievement progression target
for value_offset, name, min, max, tooltip in achievement_list:
    property_sint(value_offset + 4 * len(achievement_list), 4, None, tooltip, min, max)
category(3, 10, "progress offset", None, 1) # achievement progression offset
for value_offset, name, min, max, tooltip in achievement_list:
    property_sint(value_offset + 8 * len(achievement_list), 4, None, tooltip, min, max)

category(4, 10, "Royal stickers", tooltip="Visual representation of collected royal stickers")
for i in range(6): property_bool(offset=0x0020, index=i, name=f"SaveMenu{i+1}", thin=True, tooltip="display in save select")
category(5, 10, "") # (royal stickers in game)
for i in range(6): property_bool(offset=0x0180, index=i, name=f"OnAlbum{i+1}", thin=True, tooltip="display on album cover")

category(2, 7, None)
property_sint_enum(0x0168, 4, "Party Member", {
    "None": -1,
    "1-4 Toad": 0, # requires gf_evt_mac_kinopio_return_town to be false to show up
    "1-1 Toad": 1,
    "Wiggler1": 2,
    "Wiggler2": 3,
    "Wiggler3": 4,
    "Wiggler4": 5,
}, "current party member")

category(0, 28,"Museum")
property_sint(0x0e78, 4, "regular donations", "ammount of regular stickers donated to the museum")
property_sint(0x0e7c, 4, "thing donations", "ammount of thing stickers donated to the museum")

category(4, 17,"Unknown")
for i, (o,t) in enumerate([
    (0x0178, "counts up something (highest so far is 96)"),
    #(0x0194, "somehow relates to party members"), # does not seem to actually do anything when modified
    (0x0eec, "counts up while playing"),
]):
    if i == 2: category(4, 22, None) # extremely scuffed layout fix
    property_sint(o, 4, f"0x{o:04x}", t)

category(2, 23,"Battle Statistic (current level only)")
property_sint(0x0e68, 4, "battles won", "ammount of battles won within the current level")
# TODO: confirm
property_sint(0x0e6c, 4, "enemies defeated?", "ammount of enemies defeated within the current level")
property_sint(0x0e70, 4, "level end coin bonus", "ammount of bonus coins rewarded on level exit", min=0, max=300)

category(2, 27, "ingame Playtime")
property_uint(offset=0x0ef0, bytes=2, name="Frames", min=0, max=1799)
property_uint(offset=0x0ef2, bytes=1, name="Minutes")
property_uint(offset=0x0ef3, bytes=1, name="Hours")

category_tab("FLAGS/SWITCHES")
flag_switch_frame = tk.Frame(CURRENT_TAB_ROOT)
flag_switch_tree = ttk.Treeview(flag_switch_frame, columns=("key","value"))#, height=26)
flag_switch_tree.heading("#0", text="category")
flag_switch_tree.column("#0", width=168, stretch=False)
flag_switch_tree.heading("key", text="key")
flag_switch_tree.heading("value", text="value")
flag_switch_tree.column("value", width=64, stretch=False)

flag_switch_tree_v_scrollbar = ttk.Scrollbar(flag_switch_frame, orient=tk.VERTICAL, command=flag_switch_tree.yview)
flag_switch_tree.configure(yscrollcommand=flag_switch_tree_v_scrollbar.set)

flag_switch_tree.pack(side="left", fill="both", expand=True)
flag_switch_tree_v_scrollbar.pack(side="right", fill="y")
flag_switch_frame.pack(fill="both",expand=True)

def flag_switch_tree_edit_cell(event):
    is_keypress = event.type == "2"
    item = flag_switch_tree.selection()[0] if is_keypress else flag_switch_tree.identify_row(event.y)
    column = "#2" if is_keypress else flag_switch_tree.identify_column(event.x)
    if not item or not column:
        return
    elif column != "#2": 
        # only allow to edit values, not the other columns
        return
    index = int(column[1:]) - 1
    x, y, width, height = flag_switch_tree.bbox(item, column)

    if len(flag_switch_tree.item(item, "values")) < 2: return

    value = flag_switch_tree.item(item, "values")[index]
    if value == "True" or value == "False":
        values = list(flag_switch_tree.item(item, "values"))
        istrue = str(value == "False")
        for i in flag_items[item]:
            values = list(flag_switch_tree.item(i, "values"))
            values[index] = istrue
            flag_switch_tree.item(i, values=values)
        return
    else:
        entry = ttk.Spinbox(flag_switch_tree, increment=1, from_=0, to=255)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, flag_switch_tree.item(item, "values")[index])
        entry.select_range(0, "end")
        entry.focus()

    def save(event=None):
        for i in switch_items[item]:
            values = list(flag_switch_tree.item(i, "values"))
            values[index] = entry.get()
            flag_switch_tree.item(i, values=values)
        entry.destroy()

    entry.bind("<Return>", save)
    entry.bind("<FocusOut>", save)
    entry.bind("<Escape>", lambda e: entry.destroy())

flag_switch_tree.bind("<Double-1>", flag_switch_tree_edit_cell)
flag_switch_tree.bind("<space>", flag_switch_tree_edit_cell)
flag_switch_tree.bind("<Return>", flag_switch_tree_edit_cell)

switch_list: dict[int, list[str]] = {}
switch_items: dict[str, list[str]] = {}
def register_switches(name: str, switches: dict[str, int]):
    subtreeroot = flag_switch_tree.insert("", "end", text=name)
    for switch_name in switches:
        switch_offset = switches[switch_name]
        switch_item = flag_switch_tree.insert(subtreeroot, "end", text="", values=(switch_name, f"{read_uint(switch_offset, 1)}"))
        if switch_offset not in switch_list: switch_list[switch_offset] = []
        switch_list[switch_offset].append(switch_item)
        switch_items[switch_item] = switch_list[switch_offset]

def load_switches():
    for offset in switch_list:
        items = switch_list[offset]
        for item in items:
            values = list(flag_switch_tree.item(item, "values"))
            values[1] = read_uint(offset, 1)
            flag_switch_tree.item(item, values=values)
def save_switches():
    for offset in switch_list:
        items = switch_list[offset]
        for item in items:
            values = flag_switch_tree.item(item, "values")
            value = values[1]
            if value.isnumeric() and value.isascii():
                write_uint(offset, int(value), 1)
            break # there should only be the need to write one switch
INIT_CALLBACKS.append(load_switches)
CHANGE_CALLBACKS.append(save_switches)

flag_list: dict[tuple[int, int], list[str]] = {}
flag_items: dict[str, list[str]] = {}
def register_flags(name: str, flags: dict[str, tuple[int, int]]):
    subtreeroot = flag_switch_tree.insert("", "end", text=name)
    for flag_name in flags:
        flag_offset, flag_suboffset = flags[flag_name]
        flag_item = flag_switch_tree.insert(subtreeroot, "end", text="", values=(flag_name, f"{read_bool(flag_offset, flag_suboffset)}"))
        if (flag_offset, flag_suboffset) not in flag_list: flag_list[(flag_offset, flag_suboffset)] = []
        flag_list[(flag_offset, flag_suboffset)].append(flag_item)
        flag_items[flag_item] = flag_list[(flag_offset, flag_suboffset)]
    
def load_flags():
    for offset, suboffset in flag_list:
        items = flag_list[(offset, suboffset)]
        for item in items:
            values = list(flag_switch_tree.item(item, "values"))
            values[1] = read_bool(offset, suboffset)
            flag_switch_tree.item(item, values=values)
def save_flags():
    for offset, suboffset in flag_list:
        items = flag_list[(offset, suboffset)]
        for item in items:
            values = flag_switch_tree.item(item, "values")
            value = values[1]
            write_bool(offset, suboffset, value == "True")
            break # all flag values for the same offset are identical so only write the first
INIT_CALLBACKS.append(load_flags)
CHANGE_CALLBACKS.append(save_flags)

register_flags("Global Flags", FLAG_OFFSETS)# , 1, tooltip="story progression booleans")
register_switches("Global Switches", SWITCH_OFFSETS)# , 2, tooltip="story progression integers")
register_flags("Global mapobject Flags", MOBJ_FLAG_OFFSETS)# , 3, tooltip="map object interactions")
register_switches("Global mapobject Switches", MOBJ_SWITCH_OFFSETS)# , 4, tooltip="map object interactions")
register_flags("Global item flags", ITEM_FLAG_OFFSETS)# , 5, "picked up stickers")
register_flags("Area Flags", AF_OFFSETS)# , 6, "reset when mario exits to the world map")
register_switches("Area Switches", AS_OFFSETS)# , 7, "reset when mario exits to the world map")
register_flags("Area mapobject Flags", A_MOBJ_FLAG_OFFSETS)# , 8, "reset when mario exits to the world map")
register_switches("Area mapobject Switches", A_MOBJ_SWITCH_OFFSETS)# , 9, "reset when mario exits to the world map")
register_flags("Area item flags", A_ITEM_FLAG_OFFSETS)# , 10, "reset when mario exits to the world map")
# not sure whether those actually are flags or switches but I'm pretty certain
register_flags("Global Itemlist flags", ITEM2_FLAG_OFFSETS)# , 11, "unknown purpose, tracks when mario peels of some stickers or hits some blocks")
register_switches("Area itemlist switches", A_ITEM2_SWITCH_OFFSETS)# , 12, "most likely used to track how often mario has already hit a block")

# theoretically not flags directly but they behave exactly the same as flags
register_flags("Unlocked things", THING_UNLOCK_ORDER)

save_flag_description = scrolledtext.ScrolledText(CURRENT_TAB_ROOT, wrap="word", height=12)
save_flag_description.pack(fill="both")
save_flag_description.insert("end", """NOTE: Some switches may be 16 or 32 bits in size. These are not properly implemented yet.

Area Switches and Flags are reset when mario returns to the world map.
The Area Switches and Flags also overlap in the save file so editing one may change another aswell.

Known Flags
===========

World Map
---------
gf_wm_[A]_[B]  - connection from level A to level B unlocked
gf_wm_icon_[A] - show icon for level A
gf_wm_hana_[A] - show wiggler piece icon at level A

Abilities
---------
gf_tutorial_pepalyze           - unlock paperize ability
gf_tutorial_first_roulette_00  - unlock battle spinner
gf_pouch_get_sealbook          - unlock sticker album
gf_pouch_get_mappiece          - unlock album scrap section
gf_pouch_get_monoart           - unlock album thing section
gf_evt_mac_battle_tutorial_end - if false and the player saved in a level, mario will continue in the level

Other
-----
gf_museum_[A]_seal_[B] - donated sticker type A (robj/btl) number B to the museum
gf_*_talk_* - has heared specific dialog and can skip it
Every paperization has a flag which marks whether it has been completed yet. Sadly these do not follow a unified naming scheme.

Other
=====
- Global switches are similar to global flags but they store an 8-bit number instead.
- Global mapobject Flags are like Global Flags but tied to a specific object in the world.
- Global mapobject Switches: like mapobject flags
- Global item flags: Some stickers can only be collected once. This tracks their collection
- Collected Things: Not a flag array but it still is an array of booleans.

The 'Area' sections are like the global sections but are cleared every time mario returns to the world map. 
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
    string_dropdown = ttk.Combobox(CURRENT_TAB_ROOT, textvariable=current_string, width=32, height=48)
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
        else:
            string_dropdown["values"] = [""]
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

category_tab("PAPERIZE")
ttk.Label(CURRENT_TAB_ROOT, text="This category specifically is based on a lot of guesses.").pack()
ttk.Label(CURRENT_TAB_ROOT, text="I have not yet found a situation where any of the data in here is read by the game.").pack()

paperize_edit_enabled = tk.BooleanVar(value=False)
paperize_edit_enable = ttk.Checkbutton(CURRENT_TAB_ROOT, text="[EXPERIMENTAL] save changes for this section when saving", variable=paperize_edit_enabled).pack()
ttk.Label(CURRENT_TAB_ROOT, text="This might break since I have not checked it as much as other sections.").pack()

paperize_frame = tk.Frame(CURRENT_TAB_ROOT)
paperize_tree = ttk.Treeview(paperize_frame, columns=("checked", "type", "item"))#, height=26)
paperize_tree.heading("#0", text="Name")
#paperize_tree.column("#0", width=192, stretch=False)
paperize_tree.heading("checked", text="checked")
paperize_tree.column("checked", width=64, stretch=False)
paperize_tree.heading("type", text="unknown")
paperize_tree.column("type", width=64, stretch=False)
paperize_tree.heading("item", text="item")
paperize_tree.column("item", width=192, stretch=False)

paperize_tree_v_scrollbar = ttk.Scrollbar(paperize_frame, orient=tk.VERTICAL, command=paperize_tree.yview)
paperize_tree.configure(yscrollcommand=paperize_tree_v_scrollbar.set)

paperize_tree.pack(side="left", fill="both", expand=True)
paperize_tree_v_scrollbar.pack(side="right", fill="y")
paperize_frame.pack(fill="both",expand=True)

PAPERIZE_CLEANUP_FN = None

def paperize_tree_edit_cell(event):
    global PAPERIZE_CLEANUP_FN
    item = paperize_tree.identify_row(event.y)
    column = paperize_tree.identify_column(event.x)
    if not item or not column:
        return
    index = int(column[1:]) - 1
    x, y, width, height = paperize_tree.bbox(item, column)

    values = paperize_tree.item(item, "values")
    if index == -1: return # do not edit labels
    elif len(values) == 0: return # do not edit headers
    elif index >= len(values): return # do not edit nonexistant columns
    #print(column, item, values)
    # solved
    if index == 0:
        values = list(paperize_tree.item(item, "values"))
        values[0] = values[0] == "False"
        paperize_tree.item(item, values=values)
        paperize_tree.focus()
        return
    elif index == 1: # type (unknown specifics)
        int_range = SIGNED_INT_RANGES[2] # if index != 1 else UNSIGNED_INT_RANGES[2]
        entry = ttk.Spinbox(paperize_tree, increment=1, from_=int_range[0], to=int_range[1])
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, paperize_tree.item(item, "values")[index])
        entry.select_range(0, "end")
        entry.focus()
    elif index == 2: # item
        entry = ttk.Combobox(paperize_tree, values=ITEM_NAMES_INCLUDING_EMPTY, height=32)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, paperize_tree.item(item, "values")[index])
        entry.select_range(0, "end")
        entry.focus()
    else:
        print("INVALID")
        return

    def save(event=None):
        global PAPERIZE_CLEANUP_FN
        PAPERIZE_CLEANUP_FN = None
        values = list(paperize_tree.item(item, "values"))
        values[index] = entry.get()
        paperize_tree.item(item, values=values)
        paperize_tree.focus()
        entry.destroy()

    entry.bind("<Return>", save)
    entry.bind("<Escape>", lambda e: entry.destroy())
    PAPERIZE_CLEANUP_FN = save

paperize_tree.bind("<1>", lambda e: PAPERIZE_CLEANUP_FN() if PAPERIZE_CLEANUP_FN else None)
paperize_tree.bind("<3>", paperize_tree_edit_cell)
paperize_tree.bind("<Double-1>", paperize_tree_edit_cell)

paperize_tree_nodes = {}
for name, locknames, ismuseum in (("regular", PAPERIZE_CHECK_NAMES, False), ("museum", PAPERIZE_MUSEUM_CHECK_NAMES, True)):
    subtreeroot = paperize_tree.insert("", "end", text=name)
    paperize_tree_nodes[name] = [subtreeroot, []]
    for i, v in enumerate(locknames):
        if i == 0: continue # ignore dummy for now
        paperize_tree_nodes[name][1].append(paperize_tree.insert(subtreeroot, "end", text=v, values=("False", "0","") if not ismuseum else ("False")))

def load_paperize_data():
    # regular
    subtreeroot, subtreevalues = paperize_tree_nodes["regular"]
    for i, subtreevalue in enumerate(subtreevalues):
        locktype, lockindex, locksolved, lockitem = struct.unpack_from("hhhh", DATA, 0x11f8+(i+1)*8) 
        item = ITEM_NAMES[lockitem] if 0 <= lockitem < len(ITEM_NAMES) else "[EMPTY]"
        unknown = str(locktype)
        solved = str(locksolved == 0)
        paperize_tree.item(subtreevalue, values=(solved, unknown, item))
    # museum
    subtreeroot, subtreevalues = paperize_tree_nodes["museum"]
    for i, subtreevalue in enumerate(subtreevalues):
        lockindex, locksolved = struct.unpack_from("hh", DATA, 0x0ef4+(i+1)*4) 
        solved = str(locksolved == 0)
        paperize_tree.item(subtreevalue, values=(solved))
def save_paperize_data():
    if not paperize_edit_enabled.get(): return
    # regular
    subtreeroot, subtreevalues = paperize_tree_nodes["regular"]
    for i, subtreevalue in enumerate(subtreevalues):
        solved, unknown, item = paperize_tree.item(subtreevalue, "values")
        solved = solved == "True"
        locksolved = 0 if solved else 255
        if not unknown.isnumeric() or not unknown.isascii(): continue
        locktype = int(unknown)
        lockitem = ITEM_INDEX_LOOKUP[item] if item in ITEM_INDEX_LOOKUP else -1
        lockindex = i+1 if solved else 0
        struct.pack_into("hhhh", DATA, 0x11f8+(i+1)*8, locktype, lockindex, locksolved, lockitem)
    # museum
    subtreeroot, subtreevalues = paperize_tree_nodes["museum"]
    solvedcount = 0
    for i, subtreevalue in enumerate(subtreevalues):
        solved = paperize_tree.item(subtreevalue, "values")[0]
        solved = solved == "True"
        locksolved = 0 if solved else 255
        lockindex = i+1 if solved else 0
        struct.pack_into("hh", DATA, 0x0ef4+(i+1)*4, lockindex, locksolved)
        if solved: solvedcount += 1
    struct.pack_into("i", DATA, 0x11f4, solvedcount)

INIT_CALLBACKS.append(load_paperize_data)
CHANGE_CALLBACKS.append(save_paperize_data)

category_tab("DEFEATED NPCS")
defeated_enemies_frame = tk.Frame(CURRENT_TAB_ROOT)
defeated_enemies_tree = ttk.Treeview(defeated_enemies_frame, columns=("encounter", "defeated"))#, height=26)
defeated_enemies_tree.heading("#0", text="npc")
defeated_enemies_tree.column("#0", width=192, stretch=False)
defeated_enemies_tree.heading("encounter", text="encounter")
defeated_enemies_tree.heading("defeated", text="defeated")
defeated_enemies_tree.column("defeated", width=64, stretch=False)

defeated_enemies_tree_v_scrollbar = ttk.Scrollbar(defeated_enemies_frame, orient=tk.VERTICAL, command=defeated_enemies_tree.yview)
defeated_enemies_tree.configure(yscrollcommand=defeated_enemies_tree_v_scrollbar.set)

defeated_enemies_tree.pack(side="left", fill="both", expand=True)
defeated_enemies_tree_v_scrollbar.pack(side="right", fill="y")
defeated_enemies_frame.pack(fill="both",expand=True)

MAP_NPC_IDS_TEMP = {}
#for k in MAP_NPC_IDS: 
#    MAP_NPC_IDS_TEMP[k] = {}
#    for l in MAP_NPC_IDS[k]:
#        MAP_NPC_IDS_TEMP[k][k+": "+l] = MAP_NPC_IDS[k][l]
#for k in MAP_NPC_IDS_TEMP: 
#    for l in MAP_NPC_IDS_TEMP:
#        if l.startswith(k): 
#            for v in MAP_NPC_IDS_TEMP[l]:
#                MAP_NPC_IDS_TEMP[k][v] = MAP_NPC_IDS_TEMP[l][v]
for level in MAP_NAMES:
    for k in MAP_NAMES[level]:
        MAP_NPC_IDS_TEMP[k] = {}
        for l in MAP_NPC_IDS:
            if l.startswith(k):
                p = f"{l.removeprefix(k).removeprefix('_')}: " if k != l else ""
                for v in MAP_NPC_IDS[l]:
                    MAP_NPC_IDS_TEMP[k][p + v] = MAP_NPC_IDS[l][v]
#MAP_NPC_IDS_TEMP = MAP_NPC_IDS # fallback if the new system breaks

MAP_NPC_ID_AREAS = ["[EMPTY]"]
MAP_NPC_ID_AREAS.extend([k for k in MAP_NPC_IDS_TEMP.keys()])

ttk.Label(CURRENT_TAB_ROOT, text="Defeated NPCs will not spawn anymore. This list is cleared every time Mario returns to the world map.").pack()
ttk.Label(CURRENT_TAB_ROOT, text="Some maps handle NPC list selection via script. The NPCs from those lists might not be listed correctly.").pack()

DEFEATED_ENEMIES_CLEANUP_FN = None
defeated_enemies_tree_items = {}

def defeated_enemies_tree_item_level_root_changed(item):
    levelname = defeated_enemies_tree.item(item, "text")
    last_levelname, children = defeated_enemies_tree_items[item]
    if last_levelname == levelname: return # nothing changed
    defeated_enemies_tree_items[item][0] = levelname
    for c in children:
        defeated_enemies_tree.delete(c)
    children.clear()
    if levelname not in MAP_NPC_IDS_TEMP: return
    for enemy in MAP_NPC_IDS_TEMP[levelname]:
        children.append(defeated_enemies_tree.insert(item, "end", text=enemy, values=[MAP_NPC_IDS_TEMP[levelname][enemy][0], "False"]))

def defeated_enemies_tree_edit_cell(event):
    global DEFEATED_ENEMIES_CLEANUP_FN
    item = defeated_enemies_tree.identify_row(event.y)
    column = defeated_enemies_tree.identify_column(event.x)
    if not item or not column:
        return
    index = int(column[1:]) - 1
    x, y, width, height = defeated_enemies_tree.bbox(item, column)

    values = defeated_enemies_tree.item(item, "values")
    if index == 0: return
    if len(values) == 0 and index != -1: return
    if len(values) == 2 and index != 1: return
    if index == 1:
        values = list(defeated_enemies_tree.item(item, "values"))
        values[1] = values[1] == "False"
        defeated_enemies_tree.item(item, values=values)
        defeated_enemies_tree.focus()
        return
    elif index == -1:
        entry = ttk.Combobox(defeated_enemies_tree, values=MAP_NPC_ID_AREAS, height=32)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, defeated_enemies_tree.item(item, "text"))
        entry.select_range(0, "end")
        entry.focus()
    else:
        print("INVALID")
        return

    def save(event=None):
        global DEFEATED_ENEMIES_CLEANUP_FN
        DEFEATED_ENEMIES_CLEANUP_FN = None
        #values = list(defeated_enemies_tree.item(item, "values"))
        #values[index] = entry.get()
        defeated_enemies_tree.item(item, text=entry.get())
        defeated_enemies_tree.focus()
        entry.destroy()
        defeated_enemies_tree_item_level_root_changed(item)

    entry.bind("<Return>", save)
    entry.bind("<Escape>", lambda e: entry.destroy())
    DEFEATED_ENEMIES_CLEANUP_FN = save

defeated_enemies_tree.bind("<1>", lambda e: DEFEATED_ENEMIES_CLEANUP_FN() if DEFEATED_ENEMIES_CLEANUP_FN else None)
defeated_enemies_tree.bind("<3>", defeated_enemies_tree_edit_cell)
defeated_enemies_tree.bind("<Double-1>", defeated_enemies_tree_edit_cell)

for i in range(17):
    subtreeroot = defeated_enemies_tree.insert("", "end", text="[TODO]")
    defeated_enemies_tree_items[subtreeroot] = ["[TODO]", []]

def load_defeated_enemies():
    for i, subtreeroot in enumerate(defeated_enemies_tree_items):
        lastname, items = defeated_enemies_tree_items[subtreeroot]
        buffer = DATA[0x1fc8+i*104:0x1fc8+(i+1)*104]
        length = 0
        maxlength = 104
        while length <= maxlength and buffer[length] != 0:
            length += 1
        if length > maxlength:
            raise ValueError("STRING TOO LONG")
        level = buffer[:length].decode("utf8")
        if level == "": level = "[EMPTY]"
        length += 1 # null terminator
        while length % 4 != 0: length += 1 # alignment
        defeated_enemies_tree.item(subtreeroot, text=level)
        defeated_enemies_tree_item_level_root_changed(subtreeroot)
        if level not in MAP_NPC_IDS_TEMP: continue
            #print("l", level)
        npcs = MAP_NPC_IDS_TEMP[level]
        current_defeated_npcs = []
        while length < 104:
            current_defeated_npcs.append(struct.unpack_from("i", buffer, length)[0])
            length += 4

        for item in items:
            #print("i", item)
            encounter, identifier = ("", 0)
            name = defeated_enemies_tree.item(item, "text")
            encounter2, defeated = defeated_enemies_tree.item(item, "values")
            if name in npcs:
                encounter, identifier = npcs[name]
            if identifier == 0: continue
            defeated_enemies_tree.item(item, values=[encounter2, str(identifier in current_defeated_npcs)])
def save_defeated_enemies():
    for i, subtreeroot in enumerate(defeated_enemies_tree_items):
        lastname, items = defeated_enemies_tree_items[subtreeroot]
        buffer = bytearray(104)
        level = defeated_enemies_tree.item(subtreeroot, "text")
        if level == "[EMPTY]": level = ""
        if level in MAP_NPC_IDS_TEMP:
            #print("l", level)
            npcs = MAP_NPC_IDS_TEMP[level]
            #print("n", npcs)
            encoded = level.encode("utf8")
            encoded += b"\0"
            l = len(encoded)
            buffer[0:l] = encoded
            while l % 4 != 0: l += 1
            for item in items:
                #print("i", item)
                encounter, identifier = ("", 0)
                name = defeated_enemies_tree.item(item, "text")
                encounter2, defeated = defeated_enemies_tree.item(item, "values")
                #print(name, defeated)
                if name in npcs:
                    encounter, identifier = npcs[name]
                #print(encounter, identifier)
                if identifier == 0: continue
                if defeated != "True": continue
                if l >= 104:
                    print(f"ENCODING TOO MANY NPCS, IGNORING {name}")
                    break
                struct.pack_into("i", buffer, l, identifier)
                l += 4
        DATA[0x1fc8+i*104:0x1fc8+(i+1)*104] = buffer
        
INIT_CALLBACKS.append(load_defeated_enemies)
CHANGE_CALLBACKS.append(save_defeated_enemies)

# experimental
def add_theming():
    style = ttk.Style(root)
    theme_menu = tk.Menu(menubar)
    for name in style.theme_names():
        theme_menu.add_command(label=name, command=lambda name=name:style.theme_use(name))
    menubar.add_cascade(label="UI Theme", menu=theme_menu)
#add_theming() # this does not do anything useful but may be useful in the future

if len(sys.argv) > 1 and sys.argv[1].endswith(".bin") and os.path.isfile(sys.argv[1]): 
    load_data(sys.argv[1])
else: load_path()

root.mainloop()
