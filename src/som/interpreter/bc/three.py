def get_tos(execution_context):
    return execution_context.tos_reg3


def push_1(execution_ctx, val):
    execution_ctx.tos_reg4 = val
    execution_ctx.state = 4