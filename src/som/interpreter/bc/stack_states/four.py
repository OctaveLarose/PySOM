def get_tos(execution_ctx):
    return execution_ctx.tos_reg4


def push_1(execution_ctx, val):
    execution_ctx.tos_reg5 = val
    execution_ctx.state = 5

def pop_1(execution_ctx):
    execution_ctx.state = 3
    val = execution_ctx.tos_reg4
    return val

def pop_2(execution_ctx):
    execution_ctx.state = 2
    return execution_ctx.tos_reg4, execution_ctx.tos_reg3

def set_tos(execution_ctx, val):
    execution_ctx.tos_reg4 = val

def read_stack_elem(execution_ctx, offset):
    if offset == 0:
        return execution_ctx.tos_reg4
    elif offset == 1:
        return execution_ctx.tos_reg3
    elif offset == 2:
        return execution_ctx.tos_reg2
    elif offset == 3:
        return execution_ctx.tos_reg
    else:
        return execution_ctx.stack[execution_ctx.stack_ptr - offset + 4]