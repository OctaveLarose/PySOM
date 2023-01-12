def get_tos(execution_context):
    return execution_context.tos_reg

def push_1(execution_context, val):
    execution_context.tos_reg2 = val
    execution_context.state = 2

def pop_1(execution_ctx):
    execution_ctx.state = 0
    val = execution_ctx.tos_reg
    return val


def pop_2(execution_ctx):
    val = execution_ctx.stack[execution_ctx.stack_ptr]
    execution_ctx.stack_ptr -= 1
    return execution_ctx.tos_reg2, val


def set_tos(execution_ctx, val):
    execution_ctx.tos_reg = val

def read_stack_elem(execution_ctx, offset):
    if offset == 0:
        return execution_ctx.tos_reg
    else:
        return execution_ctx.stack[execution_ctx.stack_ptr - offset + 1]