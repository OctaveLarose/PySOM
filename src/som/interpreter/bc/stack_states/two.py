def get_tos(execution_context):
    return execution_context.tos_reg2

def push_1(execution_context, val):
    execution_context.tos_reg3 = val
    execution_context.state = 3

def pop_1(execution_ctx):
    execution_ctx.state = 1
    val = execution_ctx.tos_reg2
    return val


def pop_2(execution_ctx):
    execution_ctx.state = 0
    return execution_ctx.tos_reg2, execution_ctx.tos_reg

def set_tos(execution_ctx, val):
    execution_ctx.tos_reg2 = val

def read_stack_elem(execution_ctx, offset):
    if offset == 0:
        return execution_ctx.tos_reg2
    elif offset == 1:
        return execution_ctx.tos_reg
    else:
        return execution_ctx.stack[execution_ctx.stack_ptr - offset + 2]