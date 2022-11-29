from rlib import jit
from som.interpreter.bc.interpreter import Interpreter
from som.interpreter.bc.interpreter_tos import InterpreterTOS1
from som.interpreter.bc.method_execution_context import MethodExecutionContext
from som.interpreter.bc.base_interpreter import get_printable_location


class MultiInterpreter:
    jitdriver = jit.JitDriver(
        name="Interpreter",
        greens=["current_bc_idx", "stack_ptr", "method"],
        reds=["frame", "stack"],
        # virtualizables=['frame'],
        get_printable_location=get_printable_location,
        # the next line is a workaround around a likely bug in RPython
        # for some reason, the inlining heuristics default to "never inline" when
        # two different jit drivers are involved (in our case, the primitive
        # driver, and this one).
        # the next line says that calls involving this jitdriver should always be
        # inlined once (which means that things like Integer>>< will be inlined
        # into a while loop again, when enabling this drivers).
        should_unroll_one_iteration=lambda current_bc_idx, stack_ptr, method: True,
    )

    def __init__(self):
        pass

    def interpret(self, method, frame, max_stack_size):
        from som.vm.current import current_universe

        interpreter = Interpreter(method, frame, max_stack_size)
        interpreter2 = InterpreterTOS1(method, frame, max_stack_size)

        execution_ctx = MethodExecutionContext(max_stack_size)

        state = 0
        current_bc_idx = 0

        while True:
            self.jitdriver.jit_merge_point(
                current_bc_idx=current_bc_idx,
                stack_ptr=execution_ctx.stack_ptr,
                method=method,
                frame=frame,
                stack=execution_ctx.stack,
            )

            # TODO actually link this pseudocode with the bytecode loops
            if state == 0:
                bc_loop = interpreter.bytecode_loop
            else:
                bc_loop = interpreter2.bytecode_loop_tos

            ret_val = bc_loop(execution_ctx, current_universe)

            if ret_val is not "UNFINISHED":
                return ret_val
