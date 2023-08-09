import sys

from pathlib import Path

from core import info
from core.object_manager import ObjectManager
from miniz.concrete.module import Module
from miniz2xml.xml_builder import XMLBuilder
from zs.zs_compiler import ZSCompiler

from zs.cli.options import Options, get_options, InitOptions

from zs.std.importers import ZSImporter, ModuleImporter
from zs.modules.module_core import module as core
# from zs.std.modules.module_filesystem import filesystem
# from zs.std.modules.module_srf import srf

from zs.std.parsers import base as base_language


def main(options: Options):
    if isinstance(options, InitOptions):
        from zs import project
        return project.init(options)

    project_name = Path(options.source).name.split('.')[0].replace('_', ' ').title().replace(' ', "")

    compiler = ZSCompiler(parser=base_language.get_parser)
    context = compiler.context
    state = compiler.state

    compiler.toolchain.parser.setup()

    context.import_system.add_directory(Path(options.source).parent)

    context.import_system.add_importer(ZSImporter(compiler.context.import_system), ".zs")
    context.import_system.add_importer(ModuleImporter(compiler), "module")

    context.add_module("core", core)
    # context.add_module("srf", srf)
    # context.add_module("filesystem", filesystem)

    # try:
    #     result = compiler.toolchain.execute_document(options.source, result=ToolchainResult.ResolvedAST)
    try:
        result = compiler.import_document(options.source)
    except Exception as e:
        raise e
    else:
        # result
        module = result.object_scope.lookup_name(project_name, default=None)
        if not isinstance(module, Module):
            raise TypeError(f"Can't find a module named \'{project_name}\'")

        xml_dmp = XMLBuilder(project_name, info.INFO_DICT, ObjectManager())

        with Path(options.source).with_suffix(".xml").open("w") as xml:
            xml.write(xml_dmp.compile(module).dump())

    finally:
        state.reset()

        for message in state.messages:
            print(f"[{message.processor.__class__.__name__}] [{message.type.value}]{(' ' + str(message.origin)) if message.origin else ''} -> {message.content}")


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    main(get_options())
