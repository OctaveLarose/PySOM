from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:
    stack_ptr = -1
    tos_reg = None
    is_tos_reg_in_use = False

    def __init__(self, max_stack_size, no_tos_caching=False):
        self.stack = [None] * max_stack_size
        self.no_tos_caching = no_tos_caching

    def push_1(self, val):
        self.stack_ptr += 1
        self.stack[self.stack_ptr] = val
        # TODO modified code to make base interpreter function in isolation
        # self.tos_reg = val
        # self.is_tos_reg_in_use = True


    def push_1_tos1(self, val):
        self.stack_ptr += 1
        self.stack[self.stack_ptr] = self.tos_reg
        self.tos_reg = val

    def pop_1(self):
        val = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1
        return val

    def pop_1_tos1(self):
        val = self.tos_reg
        self.is_tos_reg_in_use = False
        return val

    def pop_2(self):  # could have a faster implem but not bothering for now
        return self.pop_1(), self.pop_1()

    def pop_2_tos1(self):  # could have a faster implem but not bothering for now
        return self.pop_1_tos1(), self.pop_1()

    def get_tos(self):
        return self.stack[self.stack_ptr]

    def get_tos_tos1(self):
        return self.tos_reg

    def set_tos(self, val):
        self.stack[self.stack_ptr] = val

    def set_tos_tos1(self, val):
        self.tos_reg = val

    def read_stack_elem(self, offset):
        return self.stack[self.stack_ptr - offset]

    def read_stack_elem_tos1(self, offset):
        if offset == 0:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 1]
