def get_tos(execution_context):
    return execution_context.stack[execution_context.stack_ptr]

def push_1(execution_context, val):
    execution_context.tos_reg = val
    execution_context.state = 1