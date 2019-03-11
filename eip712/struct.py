from collections import OrderedDict
from typing import List, Tuple

from eth_utils.crypto import keccak

from eip712.types import EIP712Type


class OrderedAttributesMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()


class _EIP712StructHelper(EIP712Type, metaclass=OrderedAttributesMeta):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type_name = cls.__name__


class EIP712Struct(_EIP712StructHelper):
    def __init__(self, **kwargs):
        super(EIP712Struct, self).__init__(self.type_name)
        members = self.get_members()
        self.values = dict()
        for name, _ in members:
            self.values[name] = kwargs.get(name)

    def encode_value(self, value=None):
        encoded_values = [typ.encode_value(self.values[name]) for name, typ in self.get_members()]
        return b''.join(encoded_values)

    def get_data_value(self, name):
        return self.values.get(name)

    def set_data_value(self, name, value):
        if name in self.values:
            self.values[name] = value

    @classmethod
    def _encode_type(cls, resolve_references: bool) -> str:
        member_sigs = [f'{typ.type_name} {name}' for name, typ in cls.get_members()]
        struct_sig = f'{cls.type_name}({",".join(member_sigs)})'

        if resolve_references:
            reference_structs = set()
            cls._gather_reference_structs(reference_structs)
            sorted_structs = sorted(list(s for s in reference_structs if s != cls), key=lambda s: s.type_name)
            for struct in sorted_structs:
                struct_sig += struct._encode_type(resolve_references=False)
        return struct_sig

    @classmethod
    def _gather_reference_structs(cls, struct_set):
        structs = [m[1] for m in cls.get_members() if isinstance(m[1], type) and issubclass(m[1], EIP712Struct)]
        for struct in structs:
            if struct not in struct_set:
                struct_set.add(struct)
                struct._gather_reference_structs(struct_set)

    @classmethod
    def encode_type(cls):
        return cls._encode_type(True)

    @classmethod
    def type_hash(cls):
        return keccak(text=cls.encode_type())

    @classmethod
    def get_members(cls) -> List[Tuple[str, EIP712Type]]:
        members = [m for m in cls.__dict__.items() if isinstance(m[1], EIP712Type)
                   or (isinstance(m[1], type) and issubclass(m[1], EIP712Struct))]
        return members
