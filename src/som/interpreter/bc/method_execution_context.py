from som.interpreter.bc.stack_states import five, four, two, one, basic, three


# the *_tos1 methods should only be invoked when is_tos_reg_in_use is True, the normal methods when False
class MethodExecutionContext:
    CANONICAL_STATE = 2

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size
        self.stack_ptr = -1

        self.tos_reg = None
        self.tos_reg2 = None
        self.tos_reg3 = None
        self.tos_reg4 = None
        self.tos_reg5 = None
        self.state = 0

    # should be used as little as possible, slow path for push_1
    def push_1_any(self, val):
        if self.state == 0:
            self.tos_reg = val
            self.state = 1
        elif self.state == 1:
            self.tos_reg2 = val
            self.state = 2
        elif self.state == 2:
            self.tos_reg3 = val
            self.state = 3
        elif self.state == 3:
            self.tos_reg4 = val
            self.state = 4
        elif self.state == 4:
            self.tos_reg5 = val
            self.state = 5
        elif self.state == 5:
            self.stack_ptr += 1
            self.stack[self.stack_ptr] = self.tos_reg
            self.tos_reg = self.tos_reg2
            self.tos_reg2 = self.tos_reg3
            self.tos_reg3 = self.tos_reg4
            self.tos_reg4 = self.tos_reg5
            self.tos_reg5 = val
        else:
            assert False, "Invalid state in push_1"

    # Slow path for pop_1.
    def pop_1_any(self):
        if self.state == 0:
            val = self.stack[self.stack_ptr]
            # if we_are_jitted():
            #     self.stack[self.stack_ptr] = None
            self.stack_ptr -= 1
            return val
        elif self.state == 1:
            self.state = 0
            val = self.tos_reg
            return val
        elif self.state == 2:
            self.state = 1
            val = self.tos_reg2
            return val
        elif self.state == 3:
            self.state = 2
            val = self.tos_reg3
            return val
        elif self.state == 4:
            self.state = 3
            val = self.tos_reg4
            return val
        elif self.state == 5:
            self.state = 4
            val = self.tos_reg5
            return val
        assert False, "Invalid state in pop_1"

    def get_tos_any(self):
        if self.state == 0:
            return self.stack[self.stack_ptr]
        elif self.state == 1:
            return self.tos_reg
        elif self.state == 2:
            return self.tos_reg2
        elif self.state == 3:
            return self.tos_reg3
        elif self.state == 4:
            return self.tos_reg4
        elif self.state == 5:
            return self.tos_reg5
        assert False, "Invalid state in get_tos_any"


    def set_tos_any(self, val):
        if self.state == 0:
            self.stack[self.stack_ptr] = val
        elif self.state == 1:
            self.tos_reg = val
        elif self.state == 2:
            self.tos_reg2 = val
        elif self.state == 3:
            self.tos_reg3 = val
        elif self.state == 4:
            self.tos_reg4 = val
        elif self.state == 5:
            self.tos_reg5 = val

    def read_stack_elem_any_state(self, offset):
        if self.state == 0:
            return basic.read_stack_elem(self, offset)
        elif self.state == 1:
            return one.read_stack_elem(self, offset)
        elif self.state == 2:
            return two.read_stack_elem(self, offset)
        elif self.state == 3:
            return three.read_stack_elem(self, offset)
        elif self.state == 4:
            return four.read_stack_elem(self, offset)
        elif self.state == 5:
            return five.read_stack_elem(self, offset)
        assert False, "Invalid state in read_stack_elem"

    def set_state_to_canonical(self, current_cache_state):
        register_values = [None, self.tos_reg, self.tos_reg2, self.tos_reg3, self.tos_reg4, self.tos_reg5]
        # the None is just so I can have a 1-based indexing for clarity while writing the algorithm.
        # TODO remove that once functional

        if current_cache_state > self.CANONICAL_STATE:
            diff = current_cache_state - self.CANONICAL_STATE

            self.stack_ptr += diff
            for i in range(diff):
                self.stack[self.stack_ptr - i] = register_values[diff - i]
            self.tos_reg = register_values[diff + 1]
            self.tos_reg2 = register_values[diff + 2]
        elif current_cache_state < self.CANONICAL_STATE:
            diff = self.CANONICAL_STATE - current_cache_state

            if diff == 2:
                self.tos_reg2 = self.stack[self.stack_ptr]
                self.tos_reg = self.stack[self.stack_ptr - 1]
                self.stack_ptr -= 2
            elif diff == 1:
                self.tos_reg2 = self.tos_reg
                self.tos_reg = self.stack[self.stack_ptr]
                self.stack_ptr -= 1

        # surprisingly unnecessary.
        # if self.stack_ptr < -1:
        #     self.stack_ptr = -1

        self.state = self.CANONICAL_STATE
