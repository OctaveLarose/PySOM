from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:
    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size
        self.stack_ptr = -1

        self.tos_reg = None
        self.tos_reg2 = None
        self.tos_reg3 = None
        self.tos_reg4 = None
        self.tos_reg5 = None
        self.state = 0

    def push_1(self, val):
        self.tos_reg = val
        self.state = 1

    def push_1_tos1(self, val):
        self.tos_reg2 = val
        self.state = 2

    def push_1_tos2(self, val):
        self.tos_reg3 = val
        self.state = 3

    def push_1_tos3(self, val):
        self.tos_reg4 = val
        self.state = 4

    def push_1_tos4(self, val):
        self.tos_reg5 = val
        self.state = 5

    def push_1_tos5(self, val):
        self.stack_ptr += 1
        self.stack[self.stack_ptr] = self.tos_reg
        self.tos_reg = self.tos_reg2
        self.tos_reg2 = self.tos_reg3
        self.tos_reg3 = self.tos_reg4
        self.tos_reg4 = self.tos_reg5
        self.tos_reg5 = val

    # should be used as little as possible, slow path for push_1
    def push_1_any(self, val):
        if self.state == 0:
            self.push_1(val)
        elif self.state == 1:
            self.push_1_tos1(val)
        elif self.state == 2:
            self.push_1_tos2(val)
        elif self.state == 3:
            self.push_1_tos3(val)
        elif self.state == 4:
            self.push_1_tos4(val)
        elif self.state == 5:
            self.push_1_tos5(val)
        else:
            assert False, "Invalid state in push_1"

    def pop_1(self): # TODO should consider adding back the we_are_jitted checks to other functions
        val = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1
        return val

    def pop_1_tos1(self):
        self.state = 0
        val = self.tos_reg
        return val

    def pop_1_tos2(self):
        self.state = 1
        val = self.tos_reg2
        return val

    def pop_1_tos3(self):
        self.state = 2
        val = self.tos_reg3
        return val

    def pop_1_tos4(self):
        self.state = 3
        val = self.tos_reg4
        return val

    def pop_1_tos5(self):
        self.state = 4
        val = self.tos_reg5
        return val

    # Slow path for pop_1.
    def pop_1_any(self):
        if self.state == 0:
            return self.pop_1()
        elif self.state == 1:
            return self.pop_1_tos1()
        elif self.state == 2:
            return self.pop_1_tos2()
        elif self.state == 3:
            return self.pop_1_tos3()
        elif self.state == 4:
            return self.pop_1_tos4()
        elif self.state == 5:
            return self.pop_1_tos5()
        assert False, "Invalid state in pop_1"

    def pop_2(self):  # could have a slightly faster implem by inlining, maybe?
        return self.pop_1(), self.pop_1()

    def pop_2_tos1(self):
        return self.pop_1_tos1(), self.pop_1()

    def pop_2_tos2(self):
        return self.pop_1_tos2(), self.pop_1_tos1()

    def pop_2_tos3(self):
        return self.pop_1_tos3(), self.pop_1_tos2()

    def pop_2_tos4(self):
        return self.pop_1_tos4(), self.pop_1_tos3()

    def pop_2_tos5(self):
        return self.pop_1_tos5(), self.pop_1_tos4()

    def get_tos(self):
        return self.stack[self.stack_ptr]

    def get_tos_tos1(self):
        return self.tos_reg

    def get_tos_tos2(self):
        return self.tos_reg2

    def get_tos_tos3(self):
        return self.tos_reg3

    def get_tos_tos4(self):
        return self.tos_reg4

    def get_tos_tos5(self):
        return self.tos_reg5

    def get_tos_any(self):
        if self.state == 0:
            return self.get_tos()
        elif self.state == 1:
            return self.get_tos_tos1()
        elif self.state == 2:
            return self.get_tos_tos2()
        elif self.state == 3:
            return self.get_tos_tos3()
        elif self.state == 4:
            return self.get_tos_tos4()
        elif self.state == 5:
            return self.get_tos_tos5()
        assert False, "Invalid state in get_tos_any"

    def set_tos(self, val):
        self.stack[self.stack_ptr] = val

    def set_tos_tos1(self, val):
        self.tos_reg = val

    def set_tos_tos2(self, val):
        self.tos_reg2 = val

    def set_tos_tos3(self, val):
        self.tos_reg3 = val

    def set_tos_tos4(self, val):
        self.tos_reg4 = val

    def set_tos_tos5(self, val):
        self.tos_reg5 = val

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

    def read_stack_elem_tos3(self, offset):
        if offset == 0:
            return self.tos_reg3
        elif offset == 1:
            return self.tos_reg2
        elif offset == 2:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 3]

    def read_stack_elem_tos4(self, offset):
        if offset == 0:
            return self.tos_reg4
        elif offset == 1:
            return self.tos_reg3
        elif offset == 2:
            return self.tos_reg2
        elif offset == 3:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr - offset + 4]

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

    def read_stack_elem_any_state(self, offset):
        if self.state == 0:
            return self.read_stack_elem(offset)
        elif self.state == 1:
            return self.read_stack_elem_tos1(offset)
        elif self.state == 2:
            return self.read_stack_elem_tos2(offset)
        elif self.state == 3:
            return self.read_stack_elem_tos3(offset)
        elif self.state == 4:
            return self.read_stack_elem_tos4(offset)
        elif self.state == 5:
            return self.read_stack_elem_tos5(offset)
        assert False, "Invalid state in read_stack_elem"