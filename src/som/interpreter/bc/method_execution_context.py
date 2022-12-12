from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:
    stack_ptr = -1
    tos_reg = None
    tos_reg2 = None
    state = 0

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size

    def push_1(self, val):
        self.tos_reg = val
        self.state = 1

    def push_1_tos1(self, val):
        self.tos_reg2 = val
        self.state = 2

    def push_1_tos2(self, val):
        self.stack_ptr += 1
        self.stack[self.stack_ptr] = self.tos_reg
        self.tos_reg = self.tos_reg2
        self.tos_reg2 = val

    def pop_1(self):
        val = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1
        return val

    def pop_1_tos1(self):
        val = self.tos_reg
        self.state = 0
        return val

    def pop_1_tos2(self):
        val = self.tos_reg2
        self.state = 1
        return val

    def pop_2(self):  # could have a faster implem but not bothering for now
        return self.pop_1(), self.pop_1()

    def pop_2_tos1(self):
        return self.pop_1_tos1(), self.pop_1()

    def pop_2_tos2(self):
        return self.pop_1_tos2(), self.pop_1_tos1()

    def get_tos(self):
        return self.stack[self.stack_ptr]

    def get_tos_tos1(self):
        return self.tos_reg

    def get_tos_tos2(self):
        return self.tos_reg2

    def set_tos(self, val):
        self.stack[self.stack_ptr] = val

    def set_tos_tos1(self, val):
        self.state = 1 # Not sure that this is necessary, or should be.
        self.tos_reg = val

    def set_tos_tos2(self, val):
        self.state = 2
        self.tos_reg2 = val

    def read_stack_elem(self, offset):
        return self.stack[self.stack_ptr - offset]

    def read_stack_elem_tos1(self, offset):
        if offset == 0:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 1]

    def read_stack_elem_tos2(self, offset):
        if offset == 0:
            return self.tos_reg2
        elif offset == 1:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 2]

    def read_stack_elem_any_state(self, offset):
        if self.state == 0:
            return self.read_stack_elem(offset)
        elif self.state == 1:
            return self.read_stack_elem_tos1(offset)
        else:
            return self.read_stack_elem_tos2(offset)