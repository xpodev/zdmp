import sys

from pathlib import Path

from core import info
from core.object_manager import ObjectManager
from dotnet import DotNETCompiler, DotNETContext
from miniz.concrete.module import Module
from miniz2xml.xml_builder import XMLBuilder
from zs.zs2miniz.toolchain import Toolchain
from zs.zs_compiler import ZSCompiler

from zs.cli.options import Options, get_options, InitOptions
from zs.processing import State

from zs.std.modules.module_core import core
from zs.std.modules.module_filesystem import filesystem
from zs.std.modules.module_srf import srf

from zs.std.parsers import base as base_language


def main(options: Options):
    if isinstance(options, InitOptions):
        from zs import project
        return project.init(options)

    project_name = Path(options.source).name.split('.')[0].replace('_', ' ').title().replace(' ', "")

    state = State()

    parser = base_language.get_parser(state)

    parser.setup()

    compiler = ZSCompiler(toolchain=Toolchain(state=state, parser=parser))
    context = compiler.toolchain.context

    context.add_module_to_cache("core", core)
    context.add_module_to_cache("srf", srf)
    context.add_module_to_cache("filesystem", filesystem)

    try:
        result = compiler.import_document(options.source)
    except Exception as e:
        raise e
    else:
        module = result.scope.lookup_name(project_name).get()
        if not isinstance(module, Module):
            raise TypeError

        xml_dmp = XMLBuilder(project_name, info.INFO_DICT, ObjectManager())

        with Path(options.source).with_suffix(".xml").open("w") as xml:
            xml.write(xml_dmp.compile(module).dump())

    finally:
        state.reset()

        for message in state.messages:
            print(f"[{message.processor.__class__.__name__}] [{message.field_type.value}] {message.origin} -> {message.content}")


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    main(get_options())
