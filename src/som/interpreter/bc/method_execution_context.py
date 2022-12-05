from rlib.jit import we_are_jitted


# push/pop should be methods of it, frankly. it's dumb passing a pointer to the class manually every time
class MethodExecutionContext:
    stack_ptr = -1
    tos_reg = None
    is_tos_reg_in_use = False

    def __init__(self, max_stack_size, no_tos_caching=False):
        self.stack = [None] * max_stack_size
        self.no_tos_caching = no_tos_caching

    def push_1_tos1(self, val):
        if not self.is_tos_reg_in_use:
            self.tos_reg = val
            self.is_tos_reg_in_use = True
        else:
            self.stack_ptr += 1
            self.stack[self.stack_ptr] = self.tos_reg
            self.tos_reg = val

    def pop_1_tos1(self):
        if self.is_tos_reg_in_use:
            val = self.tos_reg
            self.is_tos_reg_in_use = False
        else:
            val = self.stack[self.stack_ptr]
            if we_are_jitted():
                self.stack[self.stack_ptr] = None
            self.stack_ptr -= 1

        return val

    def pop_2_tos1(self):  # could have a faster implem but not bothering for now
        return self.pop_1_tos1(), self.pop_1_tos1()

    def get_tos_tos1(self):
        if self.is_tos_reg_in_use:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr]

    def set_tos_tos1(self, val):  # I think this could just set the tos_reg, maaaaybe...
        if self.is_tos_reg_in_use:
            self.tos_reg = val
        else:
            self.stack[self.stack_ptr] = val

    def read_stack_elem_tos1(self, offset):
        if not self.is_tos_reg_in_use:
            return self.stack[self.stack_ptr - offset]
    
        if self.is_tos_reg_in_use:
            if offset == 0:
                return self.tos_reg
            else:
                return self.stack[self.stack_ptr - offset + 1]

