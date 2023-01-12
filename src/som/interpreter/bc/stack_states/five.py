def get_tos(execution_context):
    return execution_context.tos_reg5

def push_1(execution_ctx, val):
    execution_ctx.stack_ptr += 1
    execution_ctx.stack[execution_ctx.stack_ptr] = execution_ctx.tos_reg
    execution_ctx.tos_reg = execution_ctx.tos_reg2
    execution_ctx.tos_reg2 = execution_ctx.tos_reg3
    execution_ctx.tos_reg3 = execution_ctx.tos_reg4
    execution_ctx.tos_reg4 = execution_ctx.tos_reg5
    execution_ctx.tos_reg5 = val

def pop_1(execution_ctx):
    execution_ctx.state = 4
    val = execution_ctx.tos_reg5
    return val


def pop_2(execution_ctx):
    execution_ctx.state = 3
    return execution_ctx.tos_reg5, execution_ctx.tos_reg4


def set_tos(execution_ctx, val):
    execution_ctx.tos_reg5 = val

def read_stack_elem(execution_ctx, offset):
    if offset == 0:
        return execution_ctx.tos_reg5
    elif offset == 1:
        return execution_ctx.tos_reg4
    elif offset == 2:
        return execution_ctx.tos_reg3
    elif offset == 3:
        return execution_ctx.tos_reg2
    elif offset == 4:
        return execution_ctx.tos_reg
    else:
        return execution_ctx.stack[execution_ctx.stack_ptr - offset + 5]