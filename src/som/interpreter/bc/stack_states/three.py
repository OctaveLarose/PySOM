def get_tos(execution_context):
    return execution_context.tos_reg3


def push_1(execution_ctx, val):
    execution_ctx.tos_reg4 = val
    execution_ctx.state = 4

def pop_1(execution_ctx):
    execution_ctx.state = 2
    val = execution_ctx.tos_reg3
    return val


def pop_2(execution_ctx):
    execution_ctx.state = 1
    return execution_ctx.tos_reg3, execution_ctx.tos_reg2


def set_tos(execution_ctx, val):
    execution_ctx.tos_reg3 = val

def read_stack_elem(execution_ctx, offset):
    if offset == 0:
        return execution_ctx.tos_reg3
    elif offset == 1:
        return execution_ctx.tos_reg2
    elif offset == 2:
        return execution_ctx.tos_reg
    else:
        return execution_ctx.stack[execution_ctx.stack_ptr - offset + 3]