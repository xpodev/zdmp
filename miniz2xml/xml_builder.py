from contextlib import contextmanager
from functools import singledispatchmethod
from xml.etree import ElementTree as et

from core.object_manager import ObjectManager
from miniz.template.template_construction import IConstructor
from miniz.interfaces.function import IFunction
from miniz.interfaces.module import IModule
from miniz.interfaces.oop import IClass, IInterface, ITypeclass, IStructure, IMethod
from miniz.vm.instruction import Instruction


class XMLBuilder:
    _root: et.Element
    _om: ObjectManager

    def __init__(self, name: str, info: dict, om: ObjectManager = None):
        self._root = et.Element("zsharp-project", attrib={
            **info,
            "project-name": name
        })
        self._om = om or ObjectManager()

    @property
    def om(self):
        return self._om

    def _sub_element(self, tag: str, attrib: dict[str, str] = None, **extra: str):
        return et.SubElement(self._root, tag, attrib or {}, **extra)

    def compile(self, item):
        self._compile(item)
        return self

    def dump(self, indent: str | None = "  "):
        if indent is not None:
            et.indent(self._root, space=indent)
        return et.tostring(self._root, encoding="unicode")

    @contextmanager
    def root(self, element: et.Element):
        root, self._root = self._root, element
        try:
            yield self._root
        finally:
            self._root = root

    @singledispatchmethod
    def _compile(self, item):
        self._sub_element(type(item).__name__).text = str(item)

    _cpl = _compile.register

    @_cpl
    def _(self, inst: Instruction):
        with self.root(self._sub_element("instruction", opcode=inst.op_code, id=self.om.get_object_id(inst))):
            if inst.operands:
                for operand in inst.operands:
                    op = getattr(inst, operand)
                    try:
                        kw = {"id": self.om.get_object_id(op, strict=True)}
                    except KeyError:
                        kw = {}
                    self._sub_element("operand", name=operand, **kw).text = str(op)

    @_cpl
    def _(self, module: IModule):
        with self.root(self._sub_element("module", id=self.om.get_object_id(module), name=module.name)):
            for specification in module.specifications:
                self._sub_element("implements", type="moduleapi", id=self.om.get_object_id(specification))

            for item in module.items:
                self.compile(item)

    @_cpl
    def _(self, cls: IClass):
        with self.root(self._sub_element("class", id=self.om.get_object_id(cls), name=cls.name if cls.name is not None else "{Anonymous}", base=self.om.get_object_id(cls.base))):
            with self.root(self._sub_element("specifications")):
                for specification in cls.specifications:
                    match specification:
                        case IInterface():
                            spec = "interface"
                        case ITypeclass():
                            spec = "typeclass"
                        case IStructure():
                            spec = "structure"
                        case _:
                            raise ValueError(f"Invalid specification type: {type(specification)}")
                    self._sub_element("implements", type=spec, id=self.om.get_object_id(specification))

            with self.root(self._sub_element("fields")):
                for field in cls.fields:
                    self._sub_element("field", id=self.om.get_object_id(field), name=field.name, type=f"{field.field_type}[{self.om.get_object_id(field.field_type)}]",
                                      binding=field.binding.value.lower())

            with self.root(self._sub_element("methods")):
                for function in cls.methods:
                    self.compile(function)

            with self.root(self._sub_element("constructors")):
                for constructor in cls.constructors:
                    self.compile(constructor)

            with self.root(self._sub_element("nested_definitions")):
                for definition in cls.nested_definitions:
                    self.compile(definition)

    @_cpl
    def _(self, fn: IFunction):
        if isinstance(fn, IMethod):
            tag = "method"
        else:
            tag = "function"

        if isinstance(fn, IConstructor):
            tag = "generic-" + tag

        with self.root(self._sub_element(tag, id=self.om.get_object_id(fn), name=fn.name if fn.name is not None else "{Anonymous}", returns=str(fn.signature.return_type))):
            with self.om.scope("param"):
                with self.root(self._sub_element("parameters")):
                    for parameter in fn.signature.positional_parameters:
                        self._sub_element("parameter", id=self.om.get_object_id(parameter), name=parameter.name, type=str(parameter.parameter_type), binding="positional",
                                          generic=str(isinstance(parameter, IConstructor)))
                    for parameter in fn.signature.named_parameters:
                        self._sub_element("parameter", id=self.om.get_object_id(parameter), name=parameter.name, type=str(parameter.parameter_type), binding="named",
                                          generic=str(isinstance(parameter, IConstructor)))
                    if fn.signature.variadic_positional_parameter:
                        self._sub_element("parameter", id=self.om.get_object_id(fn.signature.variadic_positional_parameter), name=parameter.name, type=str(parameter.parameter_type),
                                          binding="variadic-positional", generic=str(isinstance(fn.signature.variadic_positional_parameter, IConstructor)))
                    if fn.signature.variadic_named_parameter:
                        self._sub_element("parameter", id=self.om.get_object_id(fn.signature.variadic_named_parameter), name=parameter.name, type=str(parameter.parameter_type),
                                          binding="variadic-named", generic=str(isinstance(fn.signature.variadic_named_parameter, IConstructor)))

                with self.root(self._sub_element("body")):
                    if fn.body.has_body:
                        with self.root(self._sub_element("instructions")), self.om.scope("inst"):
                            for inst in fn.body.instructions:
                                self.compile(inst)
