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