def get_tos(execution_ctx):
    return execution_ctx.tos_reg4


def push_1(execution_ctx, val):
    execution_ctx.tos_reg5 = val
    execution_ctx.state = 5