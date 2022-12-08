from rlib.jit import we_are_jitted


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size
        self.stack_ptr = -1
        self.tos_reg = None
        self.is_tos_reg_in_use = False