from rlib.jit import we_are_jitted


# push/pop should be methods of it, frankly. it's dumb passing a pointer to the class manually every time
class StackInfo:
    stack_ptr = -1
    tos_reg = None
    is_tos_reg_free = True

    def __init__(self, max_stack_size):
        self.stack = [None] * max_stack_size


def push_1(val, stack_info):
    if stack_info.is_tos_reg_free:
        stack_info.tos_reg = val
        stack_info.is_tos_reg_free = False
    else:
        stack_info.stack_ptr += 1
        stack_info.stack[stack_info.stack_ptr] = stack_info.tos_reg
        stack_info.tos_reg = val


def pop_1(stack_info):
    if not stack_info.is_tos_reg_free:
        stack_info.is_tos_reg_free = True
        val = stack_info.tos_reg
    else:
        val = stack_info.stack[stack_info.stack_ptr]
        if we_are_jitted():
            stack_info.stack[stack_info.stack_ptr] = None
        stack_info.stack_ptr -= 1

    return val


def pop_2(stack_info):  # could have a faster implem but not bothering for now
    return pop_1(stack_info), pop_1(stack_info)


def get_tos(stack_info):
    if not stack_info.is_tos_reg_free:
        return stack_info.tos_reg
    else:
        return stack_info.stack[stack_info.stack_ptr]


def set_tos(val, stack_info):
    if not stack_info.is_tos_reg_free:
        stack_info.tos_reg = val
    else:
        stack_info.stack[stack_info.stack_ptr] = val


def read_stack_elem(offset, stack_info):
    if stack_info.is_tos_reg_free:
        return stack_info.stack[stack_info.stack_ptr - offset]

    if not stack_info.is_tos_reg_free:
        if offset == 0:
            return stack_info.tos_reg
        else:
            return stack_info.stack[stack_info.stack_ptr - offset + 1]

