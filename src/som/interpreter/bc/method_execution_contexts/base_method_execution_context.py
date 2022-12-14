from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class BaseContext:
    stack = [None]
    stack_ptr = -1

    tos_reg = None
    tos_reg2 = None
    tos_reg3 = None
    tos_reg4 = None
    tos_reg5 = None
    state = 0

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size

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