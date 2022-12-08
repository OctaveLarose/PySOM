from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:
    stack_ptr = -1
    tos_reg = None
    is_tos_reg_in_use = False

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size

    def pop_2(self):  # could have a faster implem but not bothering for now
        arg1 = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1

        arg2 = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1

        return arg1, arg2

    def pop_2_tos1(self):  # could have a faster implem but not bothering for now
        arg1 = self.tos_reg
        self.is_tos_reg_in_use = False

        arg2 = self.stack[self.stack_ptr]
        if we_are_jitted():
            self.stack[self.stack_ptr] = None
        self.stack_ptr -= 1

        return arg1, arg2