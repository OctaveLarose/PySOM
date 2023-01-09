def get_tos(execution_context):
    return execution_context.tos_reg

def push_1(execution_context, val):
    execution_context.tos_reg2 = val
    execution_context.state = 2