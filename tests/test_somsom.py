# import os
# import pytest
#
# @pytest.mark.parametrize(
#     "test_name",
#     [
#         "All",
#         "Mandelbrot",
#         "Queens",
#     ],
# )
# def test_somsom(test_name):
#     current_universe.reset(True)
#     core_lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../core-lib/"
#     args = [
#         "-cp",
#         ":".join([core_lib_path + "Smalltalk",
#                  core_lib_path + "TestSuite",
#                  core_lib_path + "SomSom/src/compiler",
#                  core_lib_path + "SomSom/src/vm",
#                  core_lib_path + "SomSom/src/vmobjects",
#                  core_lib_path + "SomSom/src/interpreter",
#                  core_lib_path + "SomSom/src/primitives",
#                  ]),
#         core_lib_path + "SomSom/src/vm/Main.som",
#         "-cp",
#         "Smalltalk:Examples/Benchmarks/LanguageFeatures",
#         "Examples/Benchmarks/BenchmarkHarness.som",
#         test_name,
#         "1",
#         "0",
#         "1"
#     ]
#
#     current_universe.interpret(args)
#
#     assert current_universe.last_exit_code() == 0
#
# from som.vm.current import current_universe
