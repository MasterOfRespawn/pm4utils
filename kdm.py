# built based on https://papermariotkb.wiki.gg/wiki/Sticker_Star_KDM_Reference

# experimental and thus a toggle
SIMPLIFY_ARRAYS_WHERE_POSSIBLE = True # semi stable
# try to add debug output to simplified version
TYPEOUTPUT_FORCE_DEBUG = False # unstable
# experimental: further unwrap arrays with only one element
TYPEOUTPUT_UNWRAP_POINTERS = False # unstable
# store type information in struct instead of in extra array
TYPEOUTPUT_KDM_ITEM_DATA_FIX = True # semi stable

# TODO: option to mark and unwrap single item arrays (pointers to structs)
# TODO: change structlengthparams to int offsets instead of the current name based system

class BinReader():
    buffer: bytes
    offset: int = 0
    offset_buffer: list[int] = []

    def eof(self) -> bool:
        return self.offset == len(self.buffer)
    def push_offset(self, new_offset: None|int = None):
        self.offset_buffer.append(self.offset)
        if new_offset is not None:
            self.offset = new_offset
    def pop_offset(self):
        self.offset = self.offset_buffer.pop()
    def get_offset(self) -> int:
        return self.offset
    def set_offset(self, offset: int):
        self.offset = offset
    def read_string(self) -> str:
        start = self.offset
        while self.buffer[self.offset] != 0:
            self.offset += 1
        string = self.buffer[start:self.offset].decode("utf8")
        self.offset += 1 # jump over null terminator
        self.align(4) # realign
        return string
    def read_int_le_unsigned(self, bytecount, aligned: bool = True) -> int:
        if aligned: # assume most data is aligned
            self.align(bytecount)
        value = 0
        for i in range(bytecount):
            value += self.buffer[self.offset + i] << (i * 8)
        self.offset += bytecount
        return value
    def read_bytes(self, bytecount) -> int:
        value = self.buffer[self.offset:self.offset+bytecount]
        self.offset += bytecount
        return value
    def peek_bytes(self, bytecount) -> int:
        value = self.buffer[self.offset:self.offset+bytecount]
        return value
    def read_bool(self, aligned: bool = True) -> bool:
        return self.read_u8(aligned=aligned) != 0
    def read_u8(self,aligned: bool = True) -> int:
        return self.read_int_le_unsigned(1, aligned=aligned)
    def read_u16(self, aligned: bool = True) -> int:
        return self.read_int_le_unsigned(2, aligned=aligned)
    def read_u32(self, aligned: bool = True) -> int:
        return self.read_int_le_unsigned(4, aligned=aligned)

    def align(self, alignment):
        # not the most pretty solution but it works
        while self.offset % alignment != 0: 
            self.offset += 1

    def from_buffer(buffer):
        self = BinReader()
        self.buffer = buffer
        self.offset = 0
        self.offset_buffer = []
        return self
    def from_path(path):
        self = BinReader()
        with open(path, "rb") as f:
            self.buffer = f.read()
        self.offset = 0
        self.offset_buffer = []
        return self

import struct

KDM_FILE_WORD_SIZE = 4
KDM_FILE_BASE_ALIGNMENT = KDM_FILE_WORD_SIZE
KDM_FILE_SECTION_STRINGS = 0
KDM_FILE_SECTION_UNKNOWN1 = 1
KDM_FILE_SECTION_UNKNOWN2 = 2
KDM_FILE_SECTION_NAMED_PARAMS = 3
KDM_FILE_SECTION_STRUCTURE_DEFINITIONS = 4
KDM_FILE_SECTION_DATA = 5
KDM_FILE_SECTION_DATA_TABLES = 6
KDM_FILE_SECTION_UNKNOWN7 = 7

# THIS ASSUMES 4 BYTES OF SIZE FOR ALL UNKNOWN DATA TYPES
KDM_FILE_BUILTIN_DATA_TYPE_SIZES = [
    0x04, # 0x00 	Float 	0x4 	0x4
    0x04, # 0x01 	Int 	0x4 	0x4
    0x04, # 0x02 	Unsigned int 	0x4 	0x4
    0x04, # 0x03 	String pointer 	0x4 	0x4
    0x01, # 0x04 	Boolean 	0x1 	0x1
    0x04, # 0x05 			
    0x04, # 0x06 			
    0x01, # 0x07 	Byte (8-bit integer) 	0x1 	0x1
    0x02, # 0x08 	Short (16-bit integer) 	0x2 	0x2
    0x04, # 0x09 			
    0x04, # 0x0A 	Pointer to array of Floats 	0x4 	0x4
    0x04, # 0x0B 	GUESS: Pointer to array of ints	0x4	0x4
    0x04, # 0x0C 			
    0x04, # 0x0D 	Pointer to array of String pointers 	0x4 	0x4
    0x04, # 0x0E 			
    0x04, # 0x0F 	Pointer to array of data structures (Section 4) 	0x4 	0x4
    0x04, # 0x10 	GUESS: Pointer to array of bytes	0x4	0x4
    0x04, # 0x11 	GUESS: Pointer to array of shorts	0x4	0x4
    0x04, # 0x12 			
    0x04, # 0x13 			
    0x04, # 0x14 	Pointer to array of pointers to arrays of data structures 	0x4 	0x4 
]
# assume unsigned int for all unknown ids
KDM_FILE_BUILTIN_TYPE_STRUCT_IDS = [
    "f", # 0x00 	Float 	0x4 	0x4
    "i", # 0x01 	Int 	0x4 	0x4
    "I", # 0x02 	Unsigned int 	0x4 	0x4
    "I", # 0x03 	String pointer 	0x4 	0x4
    "?", # 0x04 	Boolean 	0x1 	0x1
    "I", # 0x05 			
    "I", # 0x06 			
    "b", # 0x07 	Byte (8-bit integer) 	0x1 	0x1
    "h", # 0x08 	Short (16-bit integer) 	0x2 	0x2
    "I", # 0x09 			
    "I", # 0x0A 	Pointer to array of Floats 	0x4 	0x4
    "I", # 0x0B 	GUESS: Pointer to array of ints	0x4	0x4
    "I", # 0x0C 			
    "I", # 0x0D 	Pointer to array of String pointers 	0x4 	0x4
    "I", # 0x0E 			
    "I", # 0x0F 	Pointer to array of data structures (Section 4) 	0x4 	0x4
    "I", # 0x10 	GUESS: Pointer to array of bytes	0x4	0x4
    "I", # 0x11 	GUESS: Pointer to array of shorts	0x4	0x4
    "I", # 0x12 			
    "I", # 0x13 			
    "I", # 0x14 	Pointer to array of pointers to arrays of data structures 	0x4 	0x4 
]
KDM_FILE_BUILTIN_DATA_TYPE_NAMES = [
    "Float",
    "Int",
    "UInt",
    "String",
    "Bool",
    "UNKNOWN5",
    "UNKNOWN6",
    "Byte",
    "Short",
    "UNKNOWN9",
    "FloatArray",
    "IntArray",
    "UIntArray",
    "StringArray",
    "BoolArray",
    "StructArray",
    "ByteArray",
    "ShortArray",
    "UNKNOWN18",
    "UNKNOWN19",
    "StructArrayArray",
]

# primitive data types are 0 instead of none
def kdm_value_type_allows_null(type_id: int) -> bool:
    return 0 <= type_id <= 2 or type_id == 4 or type_id == 7 or type_id == 8

class KDMMapping:
    # NONULLTERM means not to count the null terminator in the length param
    # NullTerminator: array is always null terminated
    # RemoveNullTerminator: array does not need a null terminator, always remove it
    #                       ONLY USE THIS WHEN CERTAIN THERE ARE NO SIDE EFFECTS!!!
    lengthparams: dict[str, str] = {}
    structlengthparams: dict[int, dict[str, str]] = {}
    global_nullterminations: list[str] = []
    nullterminations: dict[int, list[str]] = {}
    nullterminations_int: dict[int, list[int]] = {}
    removenullterminations_int: dict[int, list[int]] = {}
    names: dict[int, tuple[str, list[tuple[int, str]]]] = {}
    global_arraytypes: dict[str, list[int]] = {}
    struct_arraytypes: dict[int, dict[int,list[int]]] = {}
    original_file: str = None # path to the file this has been loaded from
    def load_from_file(path: str):
        basepath = __file__.replace("kdm.py", "mappings/").replace("kdmparse.py", "mappings/")
        self = KDMMapping()
        self.lengthparams = {}
        self.structlengthparams = {}
        self.global_nullterminations = []
        self.nullterminations = {}
        self.nullterminations_int = {}
        self.removenullterminations_int = {}
        self.original_file = path
        self.global_arraytypes = {}
        self.struct_arraytypes = {}
        removenullterminations = {}
        self.names = {}
        with open(basepath + path, "r") as f:
            for line in f:
                line = line.removesuffix("\n").removesuffix("\r").split("#")[0]
                line = line.replace(" ", "").replace("\t", "") # ignore whitespace
                if line == "":
                    continue # empty line / comment
                elif line.startswith("LengthParam:"):
                    # first the parameter then the length it depends on
                    l = line.removeprefix("LengthParam:").split(":")
                    self.lengthparams[l[0]] = l[1]
                elif line.startswith("GlobalNullTerminator:"):
                    l = line.removeprefix("GlobalNullTerminator:")
                    self.global_nullterminations.append(l)
                elif line.startswith("NullTerminator:"):
                    # struct, array
                    l = line.removeprefix("NullTerminator:").split(":")
                    l[0] = int(l[0])
                    if l[0] not in self.nullterminations:
                        self.nullterminations[l[0]] = []
                    self.nullterminations[l[0]].append(l[1])
                elif line.startswith("RemoveNullTerminator:"):
                    # struct, array
                    l = line.removeprefix("RemoveNullTerminator:").split(":")
                    l[0] = int(l[0])
                    if l[0] not in removenullterminations:
                        removenullterminations[l[0]] = []
                    removenullterminations[l[0]].append(l[1])
                elif line.startswith("StructLengthParam:"):
                    # struct, length, array
                    l = line.removeprefix("StructLengthParam:").split(":")
                    l[0] = int(l[0])
                    if l[0] not in self.structlengthparams:
                        self.structlengthparams[l[0]] = {}
                    self.structlengthparams[l[0]][l[1]] = (l[2], l[3] != "NONULLTERM" if len(l) > 3 else True)
                elif line.startswith("GlobalArrayType:"):
                    # struct, length, array
                    l = line.removeprefix("GlobalArrayType:").split(":")
                    tablename = l[0]
                    if tablename not in self.global_arraytypes:
                        self.global_arraytypes[tablename] = {}
                    self.global_arraytypes[tablename] = [int(v) for v in l[1:]]
                    if not TYPEOUTPUT_UNWRAP_POINTERS and self.global_arraytypes[tablename][-1] == -1:
                        self.global_arraytypes[tablename].pop()
                elif line.startswith("StructArrayType:"):
                    # struct, length, array
                    l = line.removeprefix("StructArrayType:").split(":")
                    structid = int(l[0])
                    structfield = int(l[1])
                    arraysubtype = [int(v) for v in l[2:]]
                    if structid not in self.struct_arraytypes:
                        self.struct_arraytypes[structid] = {}
                    self.struct_arraytypes[structid][structfield] = arraysubtype
                    if not TYPEOUTPUT_UNWRAP_POINTERS and self.struct_arraytypes[structid][structfield][-1] == -1:
                        self.struct_arraytypes[structid][structfield].pop()
                elif line.startswith(":"):
                    l = line.removeprefix(":").split(":")
                    l[0] = int(l[0])
                    self.names[l[0]] = (l[1], [])
                    if l[0] not in self.structlengthparams:
                        self.structlengthparams[l[0]] = {}
                    if l[0] not in self.nullterminations:
                        self.nullterminations[l[0]] = []
                    if l[0] not in removenullterminations:
                        removenullterminations[l[0]] = {}
                else:
                    l = line.split(":")
                    if len(l) == 1: 
                        print(f"Unexpected mapping line: {line}")
                        continue # invalid line
                    self.names[int(l[0])][1].append((int(l[2]), l[3]))
        # map numeric ids to struct names
        for structid in self.structlengthparams:
            structlengthparams = self.structlengthparams[structid]
            to_replace = []
            for key in structlengthparams:
                value = structlengthparams[key]
                if value[0].startswith("_"):
                    structlengthparams[key] = (self.names[structid][1][int(value[0].removeprefix("_"))][1], value[1])
                if key.startswith("_"):
                    to_replace.append(key)
            for key in to_replace:
                structlengthparams[self.names[structid][1][int(key.removeprefix("_"))][1]] = structlengthparams[key]
                structlengthparams.pop(key)
        for structid in self.nullterminations:
            nullterminations = self.nullterminations[structid]
            for i in range(len(nullterminations)):
                value = nullterminations[i]
                if value.startswith("_"):
                    nullterminations[i] = self.names[structid][1][int(value.removeprefix("_"))][1]
        for structid in self.nullterminations:
            nullterminations = self.nullterminations[structid]
            nullterminations_int = []
            for i in range(len(nullterminations)):
                value = nullterminations[i]
                found = False
                for j, name in enumerate(self.names[structid][1]):
                    name = name[1]
                    if value == name:
                        nullterminations_int.append(j)
                        found = True
                        break
                if not found:
                    print(f"Could not match nulltermination id {value}")
            self.nullterminations_int[structid] = nullterminations_int
        for structid in removenullterminations:
            temp = removenullterminations[structid]
            removenullterminations_int = []
            for i in range(len(temp)):
                value = temp[i]
                if value.startswith("_"):
                    removenullterminations_int.append(int(value.removeprefix("_")))
                    continue
                found = False
                for j, name in enumerate(self.names[structid][1]):
                    name = name[1]
                    if value == name:
                        removenullterminations_int.append(j)
                        found = True
                        break
                if not found:
                    print(f"Could not match nulltermination id {value}")
            self.removenullterminations_int[structid] = removenullterminations_int
        return self
    def get_type_name(self, type_id: int) -> str:
        if type_id < 21:
            return KDM_FILE_BUILTIN_DATA_TYPE_NAMES[type_id]
        else:
            return self.names[type_id][0]
    def load_for_file(kdmfile): # kdmfile: KDMFile
        tablenames = [kdmfile.deref_stringptr_direct(int(tablename.split(":")[1])) for tablename in kdmfile.data_table_section]
        return KDMMapping.load_for_tablenames(tablenames)
    def load_for_tablenames(tablenames: list[str]):
        if len(tablenames) == 0: tablenames = ["[NONE]"] # kdm_sample.bin
        basepath = __file__.replace("kdm.py", "mappings/").replace("kdmparse.py", "mappings/")
        with open(basepath + "mappings.txt") as f:
            for line in f:
                l = line.removesuffix("\n").removesuffix("\r").split(":")
                if l[0] in tablenames:
                    return KDMMapping.load_from_file(l[1])
    def to_dict(self) -> dict:
        result = {}
        result["LengthParams"] = self.lengthparams
        result["StructLengthParams"] = self.structlengthparams
        result["NullTerminations"] = self.nullterminations
        result["GlobalNullTerminations"] = self.global_nullterminations
        result["GlobalArrayTypes"] = self.global_arraytypes
        result["StructArrayTypes"] = self.struct_arraytypes
        result["StructDefs"] = self.names
        return result

class KDMValue: 
    value_type: int
    value: [] # UNDEFINED FOR NOW

class KDMHeader:
    header: bytes      # b"KDMR"
    version: bytes     # b"\x00\x01\x01\x00"
    offsets: list[int] # section offsets / word size

# apparently only uses int32 and float32
class KDMParameter:
    unique_id: int # 0x00-0x01
    type_id: int  # 0x02-0x03
    name_ptr: int # 0x04-0x07
    name: str     # TODO: directly deref name ptr
    checksum: int # 0x08-0x0B (0 for last item)
    value: KDMValue # 0x0C-???? (size depends on type)

    def dbgprint(self):
        print(f"ID:{self.unique_id}|Type:{self.type_id}|Name:{self.name}|checksum:{self.checksum}|value:{self.value}")

# TODO: understand how to process
class KDMStructureDefinition:
    structure_id: int   # 0x00-0x01
    field_count: int    # 0x02-0x03
    total_field_count: int # field_count + embedded field counts (UNUSED BY SCRIPT)
    name_ptr: int       # 0x04-0x07 (unknown if this is actually a name pointer) (ALWAYS 0)
    #name: None | int    # *name_ptr
    checksum: int       # 0x08-0x0B (0 for last item)
    fields: list[int]   # 0x0C-???? (array of type ids (2bytes each, followed by two zero bytes))
    size: int           # autogenerated by fields

    fieldstring: str    # python struct string describing the struct

    def dbgprint(self):
        print(f"ID:{self.structure_id}|FieldCount:{self.field_count}|TotalFieldCount:{self.total_field_count}|Unknown:{self.name_ptr}|checksum:{self.checksum}|Size:{self.size}|fields:{self.fields}")

# TODO: improve internal representation
class KDMDataArray:
    array_id: int       # 0x00-0x01
    size_words: int     # 0x02-0x03
    value_type_id: int       # 0x04-0x07 array value type id
    total_fields: int   # 0x08-0x0B
    values: list[KDMValue]
    refcount: int
    offset: int # not stored but calculated by the script for easier lookup
    def dbgprint(self):
        print(f"ID:{self.array_id}|SizeInWords:{self.size_words}|ValueType:{self.value_type_id}|TotalFields:{self.total_fields}|Offset:{self.offset}|RefCount:{self.refcount}|values:{self.values}")
    
    def to_dict(self, file, mapping: KDMMapping, stored_arrays: dict[int, dict], debug: bool):
        if self.offset in stored_arrays:
            return stored_arrays[self.offset]
        file: KDMFile = file
        struct_type: KDMStructureDefinition = file.deref_structdef(self.value_type_id)
        result = []
        if debug:
            #wrap = {"<KdmArrayType>":self.value_type_id, "<KdmArrayTypeStr>": mapping.get_type_name(self.value_type_id), "<KdmArrayID>": self.array_id, "<KdmArrayLength>": len(self.values), "<KdmArrayValues>": result}
            wrap = {"<KdmArrayType>":self.value_type_id, "<KdmArrayTypeStr>": mapping.get_type_name(self.value_type_id), "<KdmArrayLength>": len(self.values), "<KdmArrayValues>": result}
        else:
            wrap = {"<KdmArrayType>":self.value_type_id, "<KdmArrayValues>": result}
        for value in self.values:
            if type(value) == KDMDataArray:
                result.append(value.to_dict(file, mapping, stored_arrays, debug))
            elif type(value) == tuple and len(value) == 2 and type(value[1]) == KDMDataArray:
                result.append(value[1].to_dict(file, mapping, stored_arrays, debug))
            elif type(value) == tuple and len(value) == 2 and value[1] is None:
                result.append(None)
            elif type(value) == list:
                # remove null terminator without adding it back
                for array_id in mapping.removenullterminations_int[self.value_type_id]:
                    array_value: KDMDataArray = value[array_id]
                    if array_value is None: continue # can not remove value from nonexistant array
                    if type(array_value) == tuple and len(array_value) == 2 and type(array_value[1]) == KDMDataArray:
                        inner_array = array_value[1].values
                        if len(inner_array) != 0 and inner_array[len(inner_array) - 1] is None:
                            inner_array.pop()
                if not debug:
                    for array_id in mapping.nullterminations_int[self.value_type_id]:
                        array_value: KDMDataArray = value[array_id]
                        if array_value is None: continue # can not remove value from nonexistant array
                        if type(array_value) == tuple and len(array_value) == 2 and type(array_value[1]) == KDMDataArray:
                            inner_array = array_value[1].values
                            if len(inner_array) != 0 and inner_array[len(inner_array) - 1] is None:
                                inner_array.pop()
                if len(value) != len(struct_type.fields):
                    raise ValueError("ERROR CONVERTING TO JSON (TODO: INVESTIGATE)")
                r = {}
                for i, n in enumerate(mapping.names[self.value_type_id][1]):
                    # EXPERIMENTAL: do not output parameters marked as array lengths
                    if not debug and n[1] in mapping.structlengthparams[self.value_type_id]: 
                        continue
                    v = value[i]
                    if type(v) == str:
                        v = file.deref_stringptr_direct(int(v.split(":")[1]))
                    elif type(v) == tuple and len(v) == 2 and type(v[1]) == KDMDataArray:
                        v = v[1].to_dict(file, mapping, stored_arrays, debug)
                    elif type(v) == tuple and len(v) == 2 and v[1] is None:
                        v = None
                    elif type(v) == list:
                        st = file.deref_structdef(struct_type.fields[i])
                        if len(v) != len(st.fields):
                            raise ValueError("ERROR CONVERTING TO JSON (TODO: INVESTIGATE)")
                        #t = {"<KdmType>":struct_type.fields[i]}
                        t = {}
                        for j, m in enumerate(mapping.names[struct_type.fields[i]][1]):
                            # EXPERIMENTAL: do not output parameters marked as array lengths
                            if not debug and m[1] in mapping.structlengthparams[struct_type.fields[i]]: 
                                continue
                            w = v[j]
                            if type(w) == str:
                                w = file.deref_stringptr_direct(int(w.split(":")[1]))
                            elif type(w) == tuple and len(w) == 2 and type(w[1]) == KDMDataArray:
                                w = w[1].to_dict(file, mapping, stored_arrays, debug)
                            elif type(w) == tuple and len(w) == 2 and type(w[1]) == None:
                                w = None
                            elif type(w) == list:
                                raise ValueError("UNSUPPORTED")
                            t[m[1]] = w
                        v = t
                    r[n[1]] = v
                result.append(r)
            elif type(value) == str:
                result.append(file.deref_stringptr_direct(int(value.split(":")[1])))
            else:
                result.append(value)
        stored_arrays[self.offset] = wrap
        return wrap

class KDMFile:
    header: KDMHeader
    strings: dict[int, str] # ptr -> string
    section1: list[()] # unknown (should have len 0)
    section2: list[()] # unknown (should have len 0)
    named_parameters: list[KDMParameter]
    structure_definitions: list[KDMStructureDefinition]
    data_section: list[KDMDataArray]
    data_table_section: dict[str, KDMDataArray] # TODO: are these arrays or array indices
    section7: list[()] # unknown (should have len 0)

    def __init__(self):
        self.header: KDMHeader = None
        self.strings = {}
        self.section1: list[()] = []
        self.section2: list[()] = []
        self.named_parameters: list[KDMParameter] = []
        self.structure_definitions: list[KDMStructureDefinition] = []
        self.data_section: list[KDMDataArray] = []
        self.data_table_section: dict[str, KDMDataArray] = {}
        self.section7: list[()] = []

    def dbgprint(self):
        print(f"Header:{self.header.header}|Version:{self.header.version}|Offsets:{self.header.offsets}")
        print(f"Strings: {self.strings}")
        print("Params:")
        for param in self.named_parameters:
            param.dbgprint()
        print("StructureDefinitions:")
        for structure in self.structure_definitions:
            structure.dbgprint()
        print("DATA ARRAYS:")
        for array in self.data_section:
            array.dbgprint()
        print("DATA TABLES:")
        for name in self.data_table_section:
            print(name, end=" - ")
            self.data_table_section[name].dbgprint()
    
    # check for arrays which all contain the same value type
    # -> mark those in the mapping files
    def dumptypemappings(self):
        tabletypes: dict[str, int] = {}
        structmembertypes: dict[tuple[int, int], int] = {}
        for tablename in self.data_table_section:
            table: KDMDataArray = self.data_table_section[tablename]
            # -1: undetermined table type
            tabletype = -1
            for v in table.values:
                if v is None: continue
                if type(v) != tuple or type(v[1]) != KDMDataArray: continue
                if tabletype == -1: 
                    tabletype = v[1].value_type_id
                elif tabletype != v[1].value_type_id:
                    tabletype = -1
                    break
            tabletypes[self.deref_stringptr_direct(int(tablename.split(":")[1]))] = tabletype
        for tablename in tabletypes:
            tabletype = tabletypes[tablename]
            if tabletype != -1:
                print(f"GlobalArrayType:{tablename}:{tabletype}")
        pass # TODO: complete or do manually

    def dumpstructmappings(self):
        for s in self.structure_definitions:
            # local variable for type annotations
            structdef: KDMStructureDefinition = s
            print(f":{structdef.structure_id}:UnknownStruct_{structdef.structure_id}")
            for i, field in enumerate(structdef.fields):
                print(f"{structdef.structure_id}:{i}:{field}:Unknown_{KDM_FILE_BUILTIN_DATA_TYPE_NAMES[field] if field < len(KDM_FILE_BUILTIN_DATA_TYPE_NAMES) else f'Struct{field}'}_{i}")
    
    def refcheck_list(self, l: list[KDMValue]):
        for value in l:
            if type(value) == list:
                self.refcheck_list(value)
            elif type(value) == tuple and len(value) == 2 and type(value[1]) == KDMDataArray:
                self.refcheck_array(value[1])

    def refcheck_array(self, array: KDMDataArray):
        array.refcount += 1
        self.refcheck_list(array.values)
    def refcheck(self, print_warn: bool = False):
        for tablename in self.data_table_section:
            # local variable for type annotations
            table: KDMDataArray = self.data_table_section[tablename]
            self.refcheck_array(table)
        if print_warn:
            for array in self.data_section:
                if array.refcount == 0:
                    print(f"UNREFERENCED ARRAY {array.offset}")
    
    def deref_stringptr_direct(self, ptr: int):
        return self.strings[ptr]
    def deref_stringptr(self, ptr: int):
        #return None if ptr == 0 else (self.strings[ptr] if ptr in self.strings else f"<STRPTR:{ptr}>")
        return f"<STRPTR:{ptr}:{self.strings[ptr]}>"
    def deref_structdef(self, structdefid: int) -> KDMStructureDefinition:
        for definition in self.structure_definitions:
            if definition.structure_id == structdefid:
                return definition
        return None
    def deref_arrayptr(self, ptr: int) -> KDMDataArray:
        for array in self.data_section:
            if array.offset == ptr:
                return array
        return None
    def get_datatype_size_align(self, datatype: int) -> tuple[int, int]:
        if datatype < len(KDM_FILE_BUILTIN_DATA_TYPE_SIZES):
            size = KDM_FILE_BUILTIN_DATA_TYPE_SIZES[datatype]
            return (size, size)
        return (self.deref_structdef(datatype).size, 4)
    def get_datatype_field_count(self, datatype: int) -> int:
        if datatype < len(KDM_FILE_BUILTIN_DATA_TYPE_SIZES):
            return 1
        return self.deref_structdef(datatype).total_field_count

    def struct_unwrap_arrays_recursive(self, mapping: KDMMapping, struct: dict, structtype: int): 
        if "<KdmArrayValues>" in struct: raise ValueError(f"TEMP{struct}") # failsafe
        for index, (fieldtype, fieldname) in enumerate(mapping.names[structtype][1]):
            if fieldtype > 20:
                self.struct_unwrap_arrays_recursive(mapping, struct[fieldname], fieldtype)
            if structtype in mapping.struct_arraytypes and index in mapping.struct_arraytypes[structtype]:
                struct[fieldname] = self.unwrap_array_recursive(mapping, struct[fieldname], mapping.struct_arraytypes[structtype][index])
            elif fieldname in struct and type(struct[fieldname]) == dict and "<KdmArrayValues>" in struct[fieldname]:
                struct[fieldname] = self.unwrap_array_recursive(mapping, struct[fieldname], [])
    def unwrap_array_recursive(self, mapping: KDMMapping, array: dict, expected_types: list[int]):
        if type(array) != dict or "<KdmArrayValues>" not in array: return array
        arraytype = array["<KdmArrayType>"]
        values = array["<KdmArrayValues>"]
        if arraytype > 20:
            isfirst = True
            for v in values:
                if v is None: continue
                self.struct_unwrap_arrays_recursive(mapping, v, arraytype)
                if TYPEOUTPUT_FORCE_DEBUG:
                    v["<KdmType>"] = mapping.names[array["<KdmArrayType>"]][0]
                    v["<KdmLen>"] = len(array["<KdmArrayValues>"])
                    isfirst = False
        if expected_types != [] and arraytype == expected_types[0]:
            for i in range(len(values)):
                values[i] = self.unwrap_array_recursive(mapping, values[i], expected_types[1:])
            if TYPEOUTPUT_UNWRAP_POINTERS and expected_types[1:] == [-1] and len(values) == 1:
                return values[0]
            return values
        elif TYPEOUTPUT_KDM_ITEM_DATA_FIX and len(values)>0 and type(values[0]) == dict and "<KdmArrayValues>" not in values[0]:
            # fallback: unwrap the last still wrapped pointer (kdm_item_data variant)
            values[0]["<KdmValueType>"] = arraytype
            for i in range(len(values)):
                values[i] = self.unwrap_array_recursive(mapping, values[i], expected_types[1:])
            return values
        else:
            #print("Wrapped struct left over. Check mapping and fix.")
            # unknown, try to catch back up at the next struct
            for i in range(len(values)):
                values[i] = self.unwrap_array_recursive(mapping, values[i], [])
        return array

    def to_dict(self, debug: bool = False):
        mapping: KDMMapping = KDMMapping.load_for_file(self)
        result = {}
        if debug:
            result["<KdmMetadata>"] = mapping.original_file if mapping.original_file is not None and not debug else mapping.to_dict()
        #result = {"<KdmMetadata>":mapping.original_file if mapping.original_file is not None and not debug else mapping.to_dict()}
        #result = {"<KdmMetadata>": mapping.to_dict()}
        for p in self.named_parameters:
            param: KDMParameter = p
            paramname = self.strings[param.name_ptr]
            if not debug and paramname in mapping.lengthparams:
                continue
            result[paramname] = param.value
        stored_arrays = {}
        for tablename in self.data_table_section:
            array: KDMDataArray = self.data_table_section[tablename]
            # remove null terminator
            if not debug and self.strings[int(tablename.split(":")[1])] in mapping.global_nullterminations:
                l = len(array.values)
                if array.values[l-1] is None:
                    array.values.pop()
            result[self.strings[int(tablename.split(":")[1])]] = array.to_dict(self, mapping, stored_arrays, debug)
        
        if not SIMPLIFY_ARRAYS_WHERE_POSSIBLE or debug: return result
        for key in result:
            if key == "<KdmMetadata>": continue
            value = result[key]
            if type(value) != dict: continue
            if not "<KdmArrayValues>" in value:
                self.struct_unwrap_arrays_recursive(mapping, value)
                continue
            if key in mapping.global_arraytypes:
                result[key] = self.unwrap_array_recursive(mapping, result[key], mapping.global_arraytypes[key])
            else:
                result[key] = self.unwrap_array_recursive(mapping, result[key], [])

        return result
    def to_json(self, debug:bool = False):
        import json
        return json.dumps(self.to_dict(debug), sort_keys=False, indent=1, ensure_ascii=False)
    def to_json_file(self, file, debug:bool = False):
        import json
        return json.dump(self.to_dict(debug), file, sort_keys=False, indent=1, ensure_ascii=False)

def kdm_file_read_header(file: KDMFile, reader: BinReader) -> KDMHeader:
    """read header data from reader and raise error if values are unexpected"""
    header = KDMHeader()
    header.header = reader.read_bytes(4)
    if header.header != b"KDMR":
        raise ValueError(f"Invalid header {header.header}, expected b'KDMR'")
    header.version = reader.read_bytes(4)
    if header.version != b"\x00\x01\x01\x00":
        raise ValueError(f"Invalid version {header.version}, expected b'\\x00\\x01\\x01\\x00'")
    # NOTE: wiki says this starts at 0x0C but it starts at 0x08
    header.offsets = [reader.read_u32() * KDM_FILE_WORD_SIZE for i in range(8)]
    return header

def kdm_file_read_strings(file: KDMFile, reader: BinReader):
    file.strings = {0:None}
    reader.set_offset(file.header.offsets[0])
    string_count = reader.read_u32()
    for i in range(string_count):
        offset = reader.get_offset()
        file.strings[offset] = reader.read_string()

def kdm_file_assume_empty_section(file: KDMFile, reader: BinReader, section):
    reader.set_offset(file.header.offsets[section])
    element_count = reader.read_u32()
    if element_count != 0:
        print(f"Unexected: Section {section} should have 0 elements but has {element_count}.")
        
        ## Test how section 2 is structured 
        #if section != 2: return # only section 2 in kdm_sample.bin to test
        #print(reader.buffer[file.header.offsets[section]:file.header.offsets[section+1]].hex())
        #data_length = file.header.offsets[section+1] - file.header.offsets[section] - 4
        #guessed_element_length = data_length // element_count
        #print(f"{element_count} - {data_length} - {guessed_element_length}")
        #for i in range(element_count):
        #    element_id = reader.read_u16()
        #    element_type = reader.read_u16()
        #    maybe_name_pointer = reader.read_u32() # possibly a name pointer
        #    checksum = reader.read_u32()
        #    value = kdm_file_parse_value(file, reader, element_type)
        #    print(element_id, element_type, maybe_name_pointer, checksum, value)

BUILTIN_VALUE_ARRAY_LOOKUP_TYPES = {10:0,13:3,15:-1,16:7,17:8,20:15}
def kdm_file_parse_value(file: KDMFile, reader: BinReader, value_type: int) -> KDMValue:
    # TODO: WRAP IN KDMValue
    if value_type < 21:# handle builtin types
        match value_type:
            # 32 bit value types
            case 0: # float
                return struct.unpack("f", reader.read_bytes(4))[0]
            case 1: # signed int
                return struct.unpack("<i", reader.read_bytes(4))[0]
            case 2: # unsigned int
                return reader.read_u32()
            case 3: # string pointer
                return file.deref_stringptr(reader.read_u32())
            case 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 20: # data array pointers
                # 10: pointer to float array
                # 11: GUESS: pointer it int array
                # 12: GUESS: pointer to uint array
                # 13: pointer to string pointer array
                # 14: GUESS: pointer to bool array
                # 15: pointer to data structure array
                # 16: GUESS: pointer to byte array
                # 17: GUESS: pointer to short array
                # 20: pointer to array of data structures
                ptr = reader.read_u32()
                return (f"<{value_type}:APTR:{ptr}>", file.deref_arrayptr(ptr))
            # 16 bit value types
            case 8: 
                return struct.unpack(KDM_FILE_BUILTIN_TYPE_STRUCT_IDS[value_type], reader.read_bytes(2))[0]
                return reader.read_u16()
            # 8 bit value types
            case 7:
                return struct.unpack(KDM_FILE_BUILTIN_TYPE_STRUCT_IDS[value_type], reader.read_bytes(1))[0]
                return reader.read_u8()
            case 4:
                return reader.read_bool()
            case _:
                raise ValueError(f"Invalid type id {value_type}")
    #print("DEREF STRUCTDEF", value_type)
    structure = file.deref_structdef(value_type)
    struct_fields = []
    for field in structure.fields:
        reader.align(file.get_datatype_size_align(field)[1])
        struct_fields.append(kdm_file_parse_value(file, reader, field))
    return struct_fields

def kdm_file_read_named_parameter(file: KDMFile, reader: BinReader) -> KDMParameter:
    parameter = KDMParameter()
    parameter.unique_id = reader.read_u16()
    parameter.type_id = reader.read_u16()
    parameter.name_ptr = reader.read_u32()
    parameter.name = file.deref_stringptr(parameter.name_ptr)
    parameter.checksum = reader.read_u32() # TODO: process
    parameter.value = kdm_file_parse_value(file, reader, parameter.type_id)
    return parameter

def kdm_file_read_named_parameters(file: KDMFile, reader: BinReader):
    reader.set_offset(file.header.offsets[KDM_FILE_SECTION_NAMED_PARAMS])
    file.named_parameters = []
    parameter_count = reader.read_u32()
    for i in range(parameter_count):
        file.named_parameters.append(kdm_file_read_named_parameter(file, reader))
        reader.align(KDM_FILE_BASE_ALIGNMENT)

def kdm_file_read_structure_definition(file: KDMFile, reader: BinReader) -> KDMStructureDefinition:
    structure = KDMStructureDefinition()
    structure.structure_id = reader.read_u16()
    #print("SID",structure.structure_id)
    structure.field_count = reader.read_u16()
    structure.total_field_count = 0
    structure.name_ptr = reader.read_u32() # file.deref_stringptr(reader.read_u32())
    if structure.name_ptr != 0:
        raise ValueError("Encountered structure with nonzero name pointer")
    structure.checksum = reader.read_u32() # TODO: process
    structure.size = 0
    structure.fields = []
    structure.fieldstring = ""
    for i in range(structure.field_count):
        field_type = reader.read_u16()
        #print(field_type, reader.offset)
        structure.fields.append(field_type)
        reader.align(4) # always algin to 4 byte

        # calculate size of the structure
        field_size, field_align = file.get_datatype_size_align(field_type)
        # padding
        while structure.size % field_align != 0:
            structure.size += 1
        structure.size += field_size
        structure.total_field_count += file.get_datatype_field_count(field_type)

    for f in structure.fields:
        if f < 21: 
            structure.fieldstring += KDM_FILE_BUILTIN_TYPE_STRUCT_IDS[f]
        else:
            structure.fieldstring += file.deref_structdef(f).fieldstring
    calcsize = struct.calcsize(structure.fieldstring)
    if calcsize != structure.size:
        raise ValueError(f"calculated structure size does not match struct calculated size {structure.size} {calcsize}")

    return structure

def kdm_file_read_structure_definitions(file: KDMFile, reader: BinReader):
    reader.set_offset(file.header.offsets[KDM_FILE_SECTION_STRUCTURE_DEFINITIONS])
    file.structure_definitions = []
    structure_definition_count = reader.read_u32()
    #print(structure_definition_count)
    for i in range(structure_definition_count):
        #print(f"SD {i}/{structure_definition_count}")
        file.structure_definitions.append(kdm_file_read_structure_definition(file, reader))
        reader.align(KDM_FILE_BASE_ALIGNMENT)

def kdm_file_read_data_array(file: KDMFile, reader: BinReader) -> KDMDataArray:
    array = KDMDataArray()
    array.array_id = reader.read_u16()
    if array.array_id == 0:
        raise ValueError("GOT ARRAY WITH ID 0")
    array.size_words = reader.read_u16()
    array.value_type_id = reader.read_u16()
    array.total_fields = reader.read_u16()
    array.values = []
    start_offset = reader.get_offset()
    array.offset = start_offset
    array.refcount = 0
    data_size, data_align = file.get_datatype_size_align(array.value_type_id)
    allow_zero_instead_of_null = kdm_value_type_allows_null(array.value_type_id)
    while reader.get_offset() - start_offset < array.size_words * 4:
        # check for null terminator
        isnull = True
        for byte in reader.peek_bytes(data_size):
            if byte != 0:
                isnull = False
        value = kdm_file_parse_value(file, reader, array.value_type_id)
        # only read array value if this is not a null terminator
        if allow_zero_instead_of_null or not isnull:
            array.values.append(value)
        else:
            array.values.append(None)
        reader.align(data_align) # always align
    return array
def kdm_file_read_data_arrays(file: KDMFile, reader: BinReader):
    reader.set_offset(file.header.offsets[KDM_FILE_SECTION_DATA])
    file.data_section = []
    data_array_count = reader.read_u32()
    for i in range(data_array_count):
        #print("READING ARRAY:", i,"/",data_array_count, reader.offset)
        file.data_section.append(kdm_file_read_data_array(file, reader))
        #print("DONE", reader.offset)
        #file.data_section[-1].dbgprint()
        reader.align(KDM_FILE_BASE_ALIGNMENT)

def kdm_file_read_data_tables(file: KDMFile, reader: BinReader):
    reader.set_offset(file.header.offsets[KDM_FILE_SECTION_DATA_TABLES])
    file.data_table_section = {}
    data_table_count = reader.read_u32()
    names = []
    arrays = []
    for i in range(data_table_count):
        names.append(file.deref_stringptr(reader.read_u32()))
        #names.append(reader.read_u32())
        reader.align(KDM_FILE_BASE_ALIGNMENT)
    for i in range(data_table_count):
        arrays.append(kdm_file_read_data_array(file, reader))
        #arrays.append(reader.read_u32())
        #arrays.append((reader.read_u16(),reader.read_u16()))
        reader.align(KDM_FILE_BASE_ALIGNMENT)
    for i in range(data_table_count):
        #print("N:", names[i], "A:", arrays[i])
        file.data_table_section[names[i]] = arrays[i]

def kdm_file_from_file(reader: BinReader) -> KDMFile: 
    file = KDMFile()
    file.header = kdm_file_read_header(file, reader)
    # section 0 - strings
    kdm_file_read_strings(file, reader)
    # section 1- empty / unknown
    kdm_file_assume_empty_section(file, reader, 1)
    # section 2 - structure identical to section 3 (only used in kdm_sample.bin)
    # maybe unnamed parameters
    kdm_file_assume_empty_section(file, reader, 2)
    # section 3 - named parameters
    kdm_file_read_named_parameters(file, reader)
    # section 4 structure definitions
    kdm_file_read_structure_definitions(file, reader)
    #file.dbgprint() # TEMP: (DEBUG)
    # section 5 data
    kdm_file_read_data_arrays(file, reader)
    # section 6 data tables
    kdm_file_read_data_tables(file, reader)
    # section 7 - empty / unknown
    kdm_file_assume_empty_section(file, reader, 7)

    #print("REACHED EOF:", reader.eof())

    return file

def kdm_file_from_path(path: str) -> KDMFile:
    return kdm_file_from_file(BinReader.from_path(path))

class KDMWriter:
    """
    1: recursively read all strings and store them
        - set offset to 
    2: decode structure definitions and build struct strings
    3: store constants (including dynamic ones)
    4: recursively build list of arrays and store them    
    """
    data: dict
    output: bytearray
    eof: int
    stringtable: dict[str, int]
    structtable: dict[bytes, int]
    structlengths: dict[int, tuple[int]]
    # id to packstr, field_count, field_names, size, align, simple_field_count, lengthmap[param, array, include_nullterm], nullterminations
    structinfos: dict[int, tuple[str, int, list[tuple[str, int]], int, int, int, list[tuple[str, str, bool]], list[int]]]
    current_unique_id: int

    struct_length_refs: dict

    def __init__(self, data: dict):
        self.data = data
        self.stringtable = {None:0}
        self.output = bytearray(b"KDMR\x00\x01\x01\x00") + bytearray(44 - 8)
        self.eof = 0
        self.offset = 0

        self.structinfos = {}
        self.structtable = {}
        self.structlengths = {}
        self.current_unique_id = 0

    def init_from_json(json_data: str):
        import json
        # todo: use hooks?
        return KDMWriter(json.loads(json_data))
    def init_from_json_path(json_path: str):
        import json
        with open(json_path) as f:
            return KDMWriter(json.load(f))

    def add_empty_bytes(self, count: int):
        self.output += bytes(count)
        self.offset += count

    def collect_string(self, string: str) -> int:
        # store the string if it is not already stored
        if string not in self.stringtable: 
            self.stringtable[string] = self.offset
            bstring = bytearray(string.encode("utf8")) + b"\0"
            while len(bstring) % 4 != 0:
                bstring += b"\0"
            self.output += bstring
            self.offset = len(self.output)
        return self.stringtable[string]
    
    def collect_strings(self, value):
        if type(value) == dict:
            for key in value:
                #if key.startswith("<Kdm"): continue
                value[key] = self.collect_strings(value[key])
        elif type(value) == list:
            for i in range(len(value)):
                value[i] = self.collect_strings(value[i])
        elif type(value) == str:
            return self.collect_string(value)
        return value
    
    def store_strings(self):
        self.offset = 44 # start of string table
        for key in self.data:
            if key == "<KdmMetadata>":
                continue
            self.collect_string(key)
            self.data[key] = self.collect_strings(self.data[key])
        # store string table length in elements
        struct.pack_into("I", self.output, 40, len(self.stringtable) - 1) # exclude None
        struct.pack_into("I", self.output, 8, 40) # store start of string table
        struct.pack_into("I", self.output, 8, 10) # store start of string table (divided by 4)

    def read_metadata(self):
        if "<KdmMetadata>" not in self.data:
            self.data["<KdmMetadata>"] = KDMMapping.load_for_tablenames([k for k in self.data]).to_dict()
        elif type(self.data["<KdmMetadata>"]) == str:
            self.data["<KdmMetadata>"] = KDMMapping.load_from_file(self.data["<KdmMetadata>"]).to_dict()
        metadata = self.data["<KdmMetadata>"]
        
        for i in range(21):
            self.structinfos[i] = (KDM_FILE_BUILTIN_TYPE_STRUCT_IDS[i], 1, [], KDM_FILE_BUILTIN_DATA_TYPE_SIZES[i], KDM_FILE_BUILTIN_DATA_TYPE_SIZES[i], 1, [])
        self.current_unique_id = 21
        for structid in metadata["StructDefs"]:
            sid = int(structid)
            if self.current_unique_id <= sid:
                self.current_unique_id = sid + 1
            fstr = ""
            field_count = 0
            simple_field_count = 0
            field_names = []
            total_size = 0
            for field in metadata["StructDefs"][structid][1]:
                field_type, field_name = field
                field_type = int(field_type)
                field_count += self.structinfos[field_type][1]
                field_names.append((field_name, field_type))
                while total_size % self.structinfos[field_type][4] != 0:
                    total_size += 1
                total_size += self.structinfos[field_type][3]
                fstr += self.structinfos[field_type][0]
                simple_field_count += 1
            while total_size % 4 != 0:
                total_size += 1 # 4 byte align
            lengthparams = []
            nullterms = []
            strsid = str(sid)
            if strsid in metadata["NullTerminations"]:
                nullterms = metadata["NullTerminations"][strsid]
            elif sid in metadata["NullTerminations"]: # fallback
                nullterms = metadata["NullTerminations"][sid]
            if strsid in metadata["StructLengthParams"]:
                m = metadata["StructLengthParams"][strsid]
                for length_name in m:
                    array_name, delta = m[length_name]
                    lengthparams.append((length_name, array_name, delta))
            elif sid in metadata["StructLengthParams"]: # fallback
                m = metadata["StructLengthParams"][sid]
                for length_name in m:
                    array_name, delta = m[length_name]
                    lengthparams.append((length_name, array_name, delta))
            self.structinfos[sid] = (fstr, field_count, field_names, total_size, 4, simple_field_count, lengthparams, nullterms)

    def store_dummy_section(self, section: int):
        struct.pack_into("I", self.output, 8 + section * 4, self.offset // 4) # store start of string table
        self.add_empty_bytes(4)

    def store_param(self, name: str, value):
        type_id = None
        type_str = ""
        if type(value) == int:
            type_id = 1
            type_str = "i"
        elif type(value) == float:
            type_id = 0
            type_str = "f"
        else:
            raise ValueError(f"trying to pack unsupported value type {type(value)}")
        CHECKSUM = 0 # TODO: figure out how to calculate this (if this is nessecary)
        self.output += struct.pack("HHII" + type_str, self.current_unique_id, type_id, self.stringtable[name], CHECKSUM, value)
        self.current_unique_id += 1
        self.offset += 16 # a named parameter should always be 16 bytes in size

    def store_named_parameters(self):
        section_start = self.offset
        struct.pack_into("I", self.output, 8 + 3 * 4, section_start // 4) # store start of param section
        param_count = 0
        self.add_empty_bytes(4)
        for key in self.data:
            if type(self.data[key]) == list or type(self.data[key]) == dict:
                continue
            self.store_param(key, self.data[key])
            param_count += 1
        struct.pack_into("I", self.output, section_start, param_count) # store start of string table

    def store_structdefs(self):
        section_start = self.offset
        self.add_empty_bytes(4) # struct count
        struct.pack_into("I", self.output, 8 + 4 * 4, section_start // 4) # store start of struct section
        struct_count = 0
        for i in self.structinfos:
            if i <= 20: continue # skip builtin structs
            # TODO: change to class or dict
            # packstr, field_count, field_names, size, align, simple_field_count
            structdef: tuple[str, int, list[tuple[str, int]], int, int, int] = self.structinfos[i]
            #print(i, structdef)
            struct_count += 1
            CHECKSUM = 0 # TODO: correctly calculate checksum
            self.output += struct.pack("HHII", i, structdef[5], 0, CHECKSUM)
            for name, field in structdef[2]:
                self.output += struct.pack("I", field)
            self.offset = len(self.output)

        struct.pack_into("I", self.output, section_start, struct_count)

    def null_array(self, structtype: int) -> list:
        structinfo: tuple[str, int, list[tuple[str, int]], int, int, int] = self.structinfos[structtype]
        # replace value with null
        if structtype == 0: return [0.0]
        elif structtype == 3: return [False]
        elif structtype < 21: return [0]
        else:
            r = []
            for field_name, field_type in structinfo[2]:
                r.extend(self.null_array(field_type))
            return r

    def struct_dict_to_array(self, struct: dict, structtype: int) -> list:
        # primitive data types
        if structtype < 21:
            # all known array types are in the range [10;20]
            if structtype >= 10:
                struct = self.store_array(struct)
            return [struct]
        result = []
        # packstr, field_count, field_names, size, align, simple_field_count
        structinfo: tuple[str, int, list[tuple[str, int]], int, int, int, list[tuple[str,str,bool]]] = self.structinfos[structtype]
        for array in structinfo[7]: # fix up null terminated arrays
            if struct[array] is None: continue # can not add a null terminator to a nonexistant array
            l = len(struct[array]["<KdmArrayValues>"])
            if l == 0 or struct[array]["<KdmArrayValues>"][l-1] is not None:
                struct[array]["<KdmArrayValues>"].append(None)
        for param, array, count_nullterminator in structinfo[6]:
            a = struct[array]
            if a is None:
                # count null pointers as empty array lengths
                l = 0
            elif type(a) == int:
                #print("[WARNING] ACCESSING ALREADY CONVERTED ARRAY:", param, array, a, struct)
                l = self.structlengths[a][0]
                if not count_nullterminator and self.structlengths[a][1]:
                    l -= 1
            else:
                l = len(a["<KdmArrayValues>"])
                if not count_nullterminator and l > 0 and a["<KdmArrayValues>"][l-1] is None:
                    l -= 1 # do not count null terminators in files
            struct[param] = l
        for field_name, field_type in structinfo[2]:
            value = struct[field_name]
            #print(value)
            if type(value) == dict and "<KdmArrayType>" in value:
                result.append(self.store_array(value))
            elif type(value) == dict:
                result.extend(self.struct_dict_to_array(value, field_type))
            elif value is None:
                result.extend(self.null_array(field_type))
            else:
                result.append(value)
        return result
    def struct_dict_to_bytes(self, struct_value: dict, structtype: int) -> bytearray:
        # packstr, field_count, field_names, size, align
        structinfo: tuple[str, int, list[tuple[str, int]], int, int, int] = self.structinfos[structtype]
        # empty value for null termination
        if struct_value is None:
            return bytearray(structinfo[3])
        array = self.struct_dict_to_array(struct_value, structtype)
        #print(structtype, array, struct_value)
        return struct.pack(structinfo[0], *array)
    
    def store_array(self, array: dict) -> int:
        if type(array) != dict or "<KdmArrayType>" not in array: 
            return array
        structtype = array["<KdmArrayType>"]
        # packstr, field_count, field_names, size, align
        structinfo: tuple[str, int, list[tuple[str, int]], int, int, int] = self.structinfos[structtype]
        length = len(array["<KdmArrayValues>"])
        size = length * structinfo[3]
        to_store = bytearray()
        for value in array["<KdmArrayValues>"]:
            to_store += self.struct_dict_to_bytes(value, structtype)
            while len(to_store) % structinfo[4] != 0:
                to_store += b"\0"
        if len(to_store) != size:
            #print(array["<KdmArrayValues>"])
            #print(structinfo)
            raise ValueError(f"array size {len(to_store)} is not equal to calculated size {size}")
        
        to_store = (structtype, bytes(to_store))
        #print(to_store)
        if to_store not in self.structtable:
            self.structlengths[self.offset + 8] = (len(array["<KdmArrayValues>"]), len(array["<KdmArrayValues>"])>0 and array["<KdmArrayValues>"][len(array["<KdmArrayValues>"])-1] is None)
            self.structtable[to_store] = self.offset + 8 # array header
            #print(self.structtable)
            self.output += struct.pack("HHHH", self.current_unique_id, len(to_store[1]) // 4, structtype, structinfo[1] * length)
            self.current_unique_id += 1
            self.output += to_store[1]
            self.offset = len(self.output)
        return self.structtable[to_store]
    
    def wrap_arrays_recursive_struct(self, metadata, struct, structtype):
        if type(struct) != dict: return # failsafe
        m = metadata["StructArrayTypes"][structtype] if structtype in metadata["StructArrayTypes"] else None
        for fieldid, (fieldtype, fieldname) in enumerate(metadata["StructDefs"][structtype][1]):
            if fieldname not in struct: continue # ignored length parameters in simple json output
            if fieldtype > 20:
                self.wrap_arrays_recursive_struct(metadata, struct[fieldname], fieldtype)
            elif m is not None and fieldid in m and (type(struct[fieldname]) == list or (TYPEOUTPUT_UNWRAP_POINTERS and m[fieldid][1:] == [-1])):
                arraytypes = m[fieldid]
                struct[fieldname] = {"<KdmArrayType>": arraytypes[0], "<KdmArrayValues>": struct[fieldname]}
                if TYPEOUTPUT_UNWRAP_POINTERS and arraytypes[1:] == [-1]:
                    struct[fieldname]["<KdmArrayValues>"] = [struct[fieldname]["<KdmArrayValues>"]]
                self.wrap_arrays_recursive(metadata, struct[fieldname], arraytypes[1:])
            elif type(struct[fieldname]) == dict and "<KdmArrayType>"in struct[fieldname]:
                self.wrap_arrays_recursive(metadata, struct[fieldname], [])
            elif type(struct[fieldname]) == list and len(struct[fieldname]) > 0 and type(struct[fieldname][0]) == dict and "<KdmValueType>" in struct[fieldname][0]:
                struct[fieldname] = {"<KdmArrayType>": struct[fieldname][0]["<KdmValueType>"], "<KdmArrayValues>": struct[fieldname]}
                if TYPEOUTPUT_UNWRAP_POINTERS and arraytypes[1:] == [-1]:
                    struct[fieldname]["<KdmArrayValues>"] = [struct[fieldname]["<KdmArrayValues>"]]
                self.wrap_arrays_recursive(metadata, struct[fieldname], [])
    def wrap_arrays_recursive(self, metadata, array, nexttypes):
        # TODO: if there are any issues related to nexttype -1: LOOK HERE!!!
        if TYPEOUTPUT_UNWRAP_POINTERS and nexttypes == [-1] and not "<KdmArrayValues>" in array:
            return
        for i in range(len(array["<KdmArrayValues>"])):
            value = array["<KdmArrayValues>"][i]
            if TYPEOUTPUT_UNWRAP_POINTERS and nexttypes[1:] == [-1] and type(value) == dict: 
                value = [value]
                array["<KdmArrayValues>"][i] = value
            if type(value) == list and nexttypes != []:
                nexttype = nexttypes[0]
                value = {"<KdmArrayType>": nexttype, "<KdmArrayValues>": array["<KdmArrayValues>"][i]}
                array["<KdmArrayValues>"][i] = value
            if type(value) == dict and "<KdmArrayType>" in value:
                self.wrap_arrays_recursive(metadata, value, nexttypes[1:])
            elif type(value) == dict:
                self.wrap_arrays_recursive_struct(metadata, value, array["<KdmArrayType>"])

    # TODO: apply struct nullterminations and struct lengthparams here as well
    def fix_up_arrays(self):
        metadata = self.data["<KdmMetadata>"]

        for k in [k for k in metadata["StructDefs"].keys()]:
            metadata["StructDefs"][int(k)] = metadata["StructDefs"][k]

        # ensure all indices for struct_arraytypes are numeric
        for struct in metadata["StructArrayTypes"]:
            for field in [f for f in metadata["StructArrayTypes"][struct].keys()]:
                metadata["StructArrayTypes"][struct][int(field)] = metadata["StructArrayTypes"][struct][field]
        # TODO: array unwrapping / wrapping
        for key in self.data:
            if key == "<KdmMetadata>": continue
            if key in metadata["GlobalArrayTypes"]:
                if TYPEOUTPUT_UNWRAP_POINTERS and metadata["GlobalArrayTypes"][key][1:] == [-1]:
                    self.data[key] = [self.data[key]]
                if type(self.data[key]) == list:
                    self.data[key] = {"<KdmArrayType>": metadata["GlobalArrayTypes"][key][0], "<KdmArrayValues>": self.data[key]}
                self.wrap_arrays_recursive(metadata, self.data[key], metadata["GlobalArrayTypes"][key][1:])
            elif type(self.data[key]) == list: 
                raise ValueError(f"Unrecognized list {key}")
            elif type(self.data[key]) == dict and "<KdmArrayType>" in self.data[key]:
                self.wrap_arrays_recursive(metadata, self.data[key], [])

        for key in self.data:
            if key == "<KdmMetadata>": continue
            if type(self.data[key]) != dict: continue
            # re add null terminator
            if key in metadata["GlobalNullTerminations"]:
                l = len(self.data[key]["<KdmArrayValues>"])
                if l == 0 or self.data[key]["<KdmArrayValues>"][l-1] is not None:
                    self.data[key]["<KdmArrayValues>"].append(None)
        
        for paramname in metadata["LengthParams"]:
            #print(self.data[metadata["LengthParams"][paramname]])
            self.data[paramname] = len(self.data[metadata["LengthParams"][paramname]]["<KdmArrayValues>"])

    def store_tables(self):
        section_5_start = self.offset
        self.add_empty_bytes(4) # array count
        struct.pack_into("I", self.output, 8 + 4 * 5, section_5_start // 4) # store start of data section
        
        names = []
        arrays = []
        for key in self.data:
            if key == "<KdmMetadata>": continue
            if type(self.data[key]) != dict: continue
            names.append(key)
            arrays.append(self.data[key])

        for array in arrays:
            #print(array)
            for i in range(len(array["<KdmArrayValues>"])):
                value = array["<KdmArrayValues>"][i]
                if type(value) != dict or "<KdmArrayType>" in value:
                    array["<KdmArrayValues>"][i] = self.store_array(value)
                else:
                    for v in value:
                        value[v] = self.store_array(value[v])

        array_count = len(self.structtable)
        struct.pack_into("I", self.output, section_5_start, len(self.structtable)) # store start of data section

        section_6_start = self.offset
        self.add_empty_bytes(4) # array count
        struct.pack_into("I", self.output, 8 + 4 * 6, section_6_start // 4) # store start of data tables

        # TODO: store tables
        for name in names:
            self.output += struct.pack("I", self.stringtable[name])
        for array in arrays:
            self.store_array(array)

        struct.pack_into("I", self.output, section_6_start, len(arrays)) # store start of data section

    def to_binary(self) -> bytearray:
        # prepare
        self.read_metadata()

        self.fix_up_arrays()

        # store data
        self.store_strings()
        self.store_dummy_section(1)
        self.store_dummy_section(2)
        self.store_named_parameters()
        self.store_structdefs()
        self.store_tables()
        self.store_dummy_section(7)

        #print(self.structinfos)

        #print("\n===DONE===\n")

        return self.output

def save(path: str, d: dict) -> bytearray:
    with open(path, "wb") as f:
        import copy
        f.write(KDMWriter(copy.deepcopy(d)).to_binary())
def load(path: str, debug: bool = False) -> dict:
    return kdm_file_from_file(BinReader.from_path(path)).to_dict(debug)

# old kdmparse/main.py
if __name__ == "__main__":
    from sys import argv
    import json
    
    if len(argv) <= 1 or argv[1] in ["--help", "help", "-h", "-?", "--?"]:
        selfname = argv[0] if len(argv) != 0 else "kdm.py"
        print(f"usage: python3 {selfname} [COMMAND]")
        print("Avaliable commands:")
        print("tojson [kdmpath] [jsonpath] (DEBUG)\n convert kdm file to json\n DEBUG for more verbose json")
        print("tobin [jsonpath] [kdmpath]\n convert json to kdm file")
        print("dbgprint\n legacy: print kdm arrays one by one")
        print("if no command is specified, this script will try to batch convert all provided files")
        exit(0)
    command = argv[1]
    match command:
        case "tobin": 
            f = KDMWriter.init_from_json_path(argv[2])
            with open(argv[3], "wb") as o:
                o.write(f.to_binary())
        case "tojson": 
            f = kdm_file_from_path(argv[2])
            with open(argv[3], "w") as o:
                f.to_json_file(o, len(argv)>4 and argv[4]=="DEBUG")
        case "json": 
            f = kdm_file_from_path(argv[2])
            print(f.to_json(len(argv)>3 and argv[3]=="DEBUG"))
        case "dbgprint": 
            f = kdm_file_from_path(argv[2])
            f.refcheck()
            f.dbgprint()
        case "refcheck": 
            f = kdm_file_from_path(argv[2])
            f.refcheck(True)
        case "dumpstructmappings": 
            f = kdm_file_from_path(argv[2])
            f.dumpstructmappings()
            f.dumptypemappings()
        case _:
            # convert all applicable files
            files = argv[1:]
            for f in files:
                if f.endswith(".bin"): # to json
                    o = f.removesuffix(".bin") + ".json"
                    f = kdm_file_from_path(f)
                    with open(o, "w") as o:
                        f.to_json_file(o)
                elif f.endswith(".json"): # to kdm
                    o = f.removesuffix(".json") + "_re.bin"
                    f = KDMWriter.init_from_json_path(f)
                    with open(o, "wb") as o:
                        o.write(f.to_binary())
                else: # unknown
                    # todo: better error handling
                    print(f"unknown file extension: {f}")
