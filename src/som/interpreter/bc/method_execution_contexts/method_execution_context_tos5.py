from rlib.jit import we_are_jitted
from som.interpreter.bc.method_execution_contexts.base_method_execution_context import BaseContext


class MethodExecutionContextTos4(BaseContext):
    def push_1_tos5(self, val):
        self.stack_ptr += 1
        self.stack[self.stack_ptr] = self.tos_reg
        self.tos_reg = self.tos_reg2
        self.tos_reg2 = self.tos_reg3
        self.tos_reg3 = self.tos_reg4
        self.tos_reg4 = self.tos_reg5
        self.tos_reg5 = val

    def pop_1_tos5(self):
        self.state = 4
        val = self.tos_reg5
        self.tos_reg5 = None
        return val

    def pop_2_tos5(self):
        return self.pop_1_tos5(), self.pop_1_tos4()

    def get_tos_tos5(self):
        return self.tos_reg5

    def set_tos_tos5(self, val):
        self.state = 5
        self.tos_reg5 = val

    def read_stack_elem_tos5(self, offset):
        if offset == 0:
            return self.tos_reg5
        elif offset == 1:
            return self.tos_reg4
        elif offset == 2:
            return self.tos_reg3
        elif offset == 3:
            return self.tos_reg2
        elif offset == 4:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 5]