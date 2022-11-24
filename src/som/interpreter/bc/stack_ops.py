from rlib.jit import we_are_jitted


# push/pop should be methods of it, frankly. it's dumb passing a pointer to the class manually every time
class MethodExecutionContext:
    stack_ptr = -1
    tos_reg = None
    is_tos_reg_free = True

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size

    def push_1(self, val):
        if self.is_tos_reg_free:
            self.tos_reg = val
            self.is_tos_reg_free = False
        else:
            self.stack_ptr += 1
            self.stack[self.stack_ptr] = self.tos_reg
            self.tos_reg = val

    def pop_1(self):
        if not self.is_tos_reg_free:
            self.is_tos_reg_free = True
            val = self.tos_reg
        else:
            val = self.stack[self.stack_ptr]
            if we_are_jitted():
                self.stack[self.stack_ptr] = None
            self.stack_ptr -= 1
    
        return val

    def pop_2(self):  # could have a faster implem but not bothering for now
        return self.pop_1(), self.pop_1()

    def get_tos(self):
        if not self.is_tos_reg_free:
            return self.tos_reg
        else:
            return self.stack[self.stack_ptr]

    def set_tos(self, val):
        if not self.is_tos_reg_free:
            self.tos_reg = val
        else:
            self.stack[self.stack_ptr] = val

    def read_stack_elem(self, offset):
        if self.is_tos_reg_free:
            return self.stack[self.stack_ptr - offset]
    
        if not self.is_tos_reg_free:
            if offset == 0:
                return self.tos_reg
            else:
                return self.stack[self.stack_ptr - offset + 1]

