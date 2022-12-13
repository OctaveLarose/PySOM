from rlib.jit import we_are_jitted
from som.interpreter.bc.method_execution_contexts.base_method_execution_context import BaseContext


class MethodExecutionContextTos1(BaseContext):
    def push_1(self, val):
        BaseContext.tos_reg2 = val
        BaseContext.state = 2

    def pop_1(self):
        BaseContext.state = 0
        val = BaseContext.tos_reg
        return val

    def pop_2(self):
        val1 = self.pop_1()
        val = BaseContext.stack[BaseContext.stack_ptr]
        if we_are_jitted():
            BaseContext.stack[BaseContext.stack_ptr] = None
        BaseContext.stack_ptr -= 1
        return val1, val

    def get_tos(self):
        return BaseContext.tos_reg

    def set_tos(self, val):
        BaseContext.state = 1 # TODO Not sure that this is necessary, or that it should be.
        BaseContext.tos_reg = val

    def read_stack_elem(self, offset):
        if offset == 0:
            return BaseContext.tos_reg
        else:
            return BaseContext.stack[BaseContext.stack_ptr - offset + 1]