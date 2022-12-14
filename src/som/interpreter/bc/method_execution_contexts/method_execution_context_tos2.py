from rlib.jit import we_are_jitted
from som.interpreter.bc.method_execution_contexts.base_method_execution_context import BaseContext


class MethodExecutionContextTos2(BaseContext):

    def push_1(self, val):
        BaseContext.tos_reg3 = val
        BaseContext.state = 3

    def pop_1_tos2(self):
        self.state = 1
        val = self.tos_reg2
        self.tos_reg2 = None
        return val

    def pop_2_tos2(self):
        return self.pop_1_tos2(), self.pop_1_tos1()

    def get_tos_tos2(self):
        return self.tos_reg2

    def set_tos_tos2(self, val):
        self.state = 2
        self.tos_reg2 = val

    def read_stack_elem_tos2(self, offset):
        if offset == 0:
            return self.tos_reg2
        elif offset == 1:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 2]
