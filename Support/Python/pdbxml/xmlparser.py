import xml.etree.ElementTree as et

from .ctype import (
    CStruct, CUnion, CEnum, CBits,
    CAttrTerm, CTypeRef, CArr, CPtr, CFunc
)
from .primtypes import PrimTypes
from .typeattrs import TypeAttrs
from .callconvs import CallConvs


class XmlParser(object):
    def __init__(self, path):
        tree = et.parse(path)
        root = tree.getroot()
        self.root = root
        self._loc_func = Locator(root[0])
        self._loc_unnamed = Locator(root[1])
        self._named = root[2]

    def _read_named(self, e_type):
        return self._read_group(e_type)

    def _read_unnamed(self, id):
        e_unnamed = self._loc_unnamed.find(id)
        return self._read_group(e_unnamed)

    def _read_group(self, e_type):
        if e_type.tag == 'enum':
            return self._read_enum(e_type)
        else:
            tree = CStruct() if e_type.tag == 'struct' else CUnion()
            return self._read_tree(e_type, tree)

    def _read_tree(self, e_type, t):
        for e_field in e_type:
            name = e_field.attrib['name']
            # TODO? offset
            # TODO? merge into _read_field()
            typ = self._read_field(e_field)
            t.add(typ, name)
        return t

    def _read_enum(self, e_type):
        t = CEnum()
        for e_const in e_type:
            name = e_const.attrib['name']
            val = e_const.attrib['val']
            t.add(name, val)
        return t

    def _read_field(self, e_field):
        if e_field.tag == 'bit-field':
            t = self._read_type(e_field, False)
            t = CBits(t, int(e_field.attrib['len']))
        else:
            t = self._read_type(e_field, True)
        return t

    def _read_type(self, e_field, has_wrap):
        attrs = e_field.attrib
        t = self._read_base(attrs['base'])
        if 'attr' in attrs:
            t = CAttrTerm(t, self._read_attr(attrs['attr']))
        if has_wrap:
            t = self._read_wrap(attrs['wrap'], t)
        return t

    def _read_attr(self, attr):
        attr_set = set()
        for s in attr.split():
            attr_set.add(TypeAttrs.lookup(s))
        return attr_set

    def _read_base(self, base):
        sigil = base[0]
        name = base[1:]
        if sigil == '.':
            return self._read_prim(name)
        elif sigil == '$':
            return self._read_type_ref(name)
        else:
            return self._read_unnamed(int(name))

    # TODO define this as a class var
    __primTypes = {
        'VOID':         PrimTypes.VOID,
        'WCHAR':        PrimTypes.WCHAR,

        'CHAR':         PrimTypes.CHAR,
        'UCHAR':        PrimTypes.UCHAR,
        'SHORT':        PrimTypes.SHORT,
        'USHORT':       PrimTypes.USHORT,
        'INT':          PrimTypes.INT,
        'UINT':         PrimTypes.UINT,
        'LONG':         PrimTypes.LONG,
        'ULONG':        PrimTypes.ULONG,

        'LONGLONG':     PrimTypes.LONGLONG,
        'ULONGLONG':    PrimTypes.ULONGLONG,

        'FLOAT':        PrimTypes.FLOAT,
        'DOUBLE':       PrimTypes.DOUBLE,
    }

    def _read_prim(self, name):
        return XmlParser.__primTypes[name]

    def _read_type_ref(self, name):
        return CTypeRef(name)

    def _read_wrap(self, wrap, t):
        arr = wrap.split()
        i = 0
        while i < len(arr):
            c = arr[i]
            if c == 'a':
                t = CArr(t, int(arr[i + 1]))
                i += 2
            elif c == 'p':
                t = CPtr(t)
                i += 1
            else:
                conv = CallConvs.stdcall if c == 'F' else CallConvs.default
                t = self._read_func(int(arr[i + 1]), t, conv)
                i += 2
        return t

    def _read_func(self, id, t, conv):
        e_func = self._loc_func.find(id)
        t = CFunc(t, conv)
        for e_arg in e_func:
            t.add(self._read_type(e_arg, True))
        return t

    def read_to_storage(self, storage):
        for e_type in self._named:
            name = e_type.attrib['name']
            type = self._read_named(e_type)
            storage.add(name, type)


class Locator(object):
    def __init__(self, elem):
        self._elem = elem
        self._index = -1

    def find(self, id):
        self._index += 1
        child = self._elem[self._index]
        # assert int(child.attrib['id']) == id
        # BELOW: for TEST purposes
        if int(child.attrib['id']) != id:
            print("warn: need id %d but current id is %s" % (id, child.attrib['id']))
            return self._elem.findall(".//*[@id='%s']" % id)[0]
        return child
