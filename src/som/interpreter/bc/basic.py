def get_tos(execution_context):
    return execution_context.stack[execution_context.stack_ptr]

def push_1(execution_context, val):
    execution_context.tos_reg = val
    execution_context.state = 1

def pop_1(execution_ctx): # TODO should consider adding back the we_are_jitted checks to other functions
    val = execution_ctx.stack[execution_ctx.stack_ptr]
    # if we_are_jitted():
    #     execution_ctx.stack[execution_ctx.stack_ptr] = None
    execution_ctx.stack_ptr -= 1
    return val

def pop_2(execution_ctx):  # could have a slightly faster implem by inlining, maybe?
    return pop_1(execution_ctx), pop_1(execution_ctx)


def set_tos(execution_ctx, val):
    execution_ctx.stack[execution_ctx.stack_ptr] = val

def read_stack_elem(execution_ctx, offset):
    return execution_ctx.stack[execution_ctx.stack_ptr - offset]