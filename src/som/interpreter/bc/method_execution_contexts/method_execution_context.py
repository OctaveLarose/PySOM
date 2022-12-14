from rlib.jit import we_are_jitted
from som.interpreter.bc.method_execution_contexts.base_method_execution_context import BaseContext


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext(BaseContext):
    def push_1(self, val):
        self.tos_reg = val
        self.state = 1

    def pop_1(self): # TODO should consider adding back the we_are_jitted checks to other functions
        val = BaseContext.stack[BaseContext.stack_ptr]
        if we_are_jitted():
            BaseContext.stack[BaseContext.stack_ptr] = None
        BaseContext.stack[BaseContext.stack_ptr] = None # TEMPORARILY SETTING ALL VALUES TO NONE AFTER POP TODO REMOVE
        BaseContext.stack_ptr -= 1
        return val

    def pop_2(self):  # could have a slightly faster implem by inlining, maybe?
        return self.pop_1(), self.pop_1()

    def get_tos(self):
        return self.stack[self.stack_ptr]

    def set_tos(self, val):
        self.stack[self.stack_ptr] = val

    def read_stack_elem(self, offset):
        return self.stack[self.stack_ptr - offset]