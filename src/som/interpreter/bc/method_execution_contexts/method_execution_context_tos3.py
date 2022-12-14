from rlib.jit import we_are_jitted
from som.interpreter.bc.method_execution_contexts.base_method_execution_context import BaseContext


class MethodExecutionContextTos3(BaseContext):

    def push_1_tos3(self, val):
        self.tos_reg4 = val
        self.state = 4

    def pop_1_tos3(self):
        self.state = 2
        val = self.tos_reg3
        self.tos_reg3 = None
        return val

    def pop_2_tos3(self):
        return self.pop_1_tos3(), self.pop_1_tos2()

    def get_tos_tos3(self):
        return self.tos_reg3

    def set_tos_tos3(self, val):
        self.state = 3
        self.tos_reg3 = val

    def read_stack_elem_tos3(self, offset):
        if offset == 0:
            return self.tos_reg3
        elif offset == 1:
            return self.tos_reg2
        elif offset == 2:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 3]