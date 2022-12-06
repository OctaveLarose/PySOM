from rlib import jit
from rlib.debug import make_sure_not_resized

from som.vm.globals import nilObject, trueObject
from som.interpreter.ast.frame import (
    _erase_obj,
    _erase_list,
    FRAME_AND_INNER_RCVR_IDX,
    _FRAME_INNER_IDX,
    _INNER_ON_STACK_IDX,
    _FRAME_AND_INNER_FIRST_ARG,
    read_frame,
)

# Frame Design Notes
#
# The design of the frame for the bytecode-based interpreters is pretty much the
# same as the design for the AST-based interpreter.
#
#   Frame
#
#  +-----------+
#  | Inner     | (Optional: for args/vars accessed from inner scopes, and non-local returns)
#  +-----------+
#  | Receiver  |
#  +-----------+
#  | Arg 1     |
#  | ...       |
#  | Arg n     |
#  +-----------+
#  | Local 1   |
#  | ...       |
#  | Local n   |
#  +-----------+


def create_frame(
    arg_inner_access_reversed,
    size_frame,
    size_inner,
    execution_ctx,
    num_args,
):
    frame = [_erase_obj(nilObject)] * size_frame
    make_sure_not_resized(frame)

    if execution_ctx.is_tos_reg_in_use:
        receiver = execution_ctx.read_stack_elem_tos1(num_args - 1)
    else:
        receiver = execution_ctx.read_stack_elem(num_args - 1)

    assert num_args - 1 == len(arg_inner_access_reversed)  # num_args without rcvr

    if size_inner > 0:
        inner = [nilObject] * size_inner
        make_sure_not_resized(inner)
        frame[FRAME_AND_INNER_RCVR_IDX] = _erase_obj(receiver)
        frame[_FRAME_INNER_IDX] = _erase_list(inner)

        inner[_INNER_ON_STACK_IDX] = trueObject
        inner[FRAME_AND_INNER_RCVR_IDX] = receiver
        _set_arguments_with_inner(
            frame,
            inner,
            arg_inner_access_reversed,
            execution_ctx,
            num_args - 1,
        )
    else:
        frame[0] = _erase_list(None)
        frame[FRAME_AND_INNER_RCVR_IDX] = _erase_obj(receiver)
        _set_arguments_without_inner(frame, execution_ctx, num_args - 1)

    return frame


def create_frame_3(
    arg_inner_access_reversed,
    size_frame,
    size_inner,
    receiver,
    arg1,
    arg2,
):
    frame = [_erase_obj(nilObject)] * size_frame
    make_sure_not_resized(frame)

    if size_inner > 0:
        inner = [nilObject] * size_inner
        make_sure_not_resized(inner)
        frame[FRAME_AND_INNER_RCVR_IDX] = _erase_obj(receiver)
        frame[_FRAME_INNER_IDX] = _erase_list(inner)

        inner[_INNER_ON_STACK_IDX] = trueObject
        inner[FRAME_AND_INNER_RCVR_IDX] = receiver
        if arg_inner_access_reversed[1]:
            inner[FRAME_AND_INNER_RCVR_IDX + 1] = arg1
            if arg_inner_access_reversed[0]:
                inner[FRAME_AND_INNER_RCVR_IDX + 2] = arg2
            else:
                frame[FRAME_AND_INNER_RCVR_IDX + 1] = _erase_obj(arg2)
        else:
            frame[FRAME_AND_INNER_RCVR_IDX + 1] = _erase_obj(arg1)
            if arg_inner_access_reversed[0]:
                inner[FRAME_AND_INNER_RCVR_IDX + 1] = arg2
            else:
                frame[FRAME_AND_INNER_RCVR_IDX + 2] = _erase_obj(arg2)
    else:
        frame[0] = _erase_list(None)
        frame[FRAME_AND_INNER_RCVR_IDX] = _erase_obj(receiver)
        frame[FRAME_AND_INNER_RCVR_IDX + 1] = _erase_obj(arg1)
        frame[FRAME_AND_INNER_RCVR_IDX + 2] = _erase_obj(arg2)

    return frame


@jit.unroll_safe
def _set_arguments_without_inner(
    frame, execution_ctx, num_args_without_rcvr
):
    arg_i = num_args_without_rcvr - 1
    frame_i = _FRAME_AND_INNER_FIRST_ARG

    while arg_i >= 0:
        obj = None
        if execution_ctx.is_tos_reg_in_use:
            obj = execution_ctx.read_stack_elem_tos1(arg_i)
        else:
            obj = execution_ctx.read_stack_elem(arg_i)

        frame[frame_i] = _erase_obj(obj)
        frame_i += 1
        arg_i -= 1


@jit.unroll_safe
def _set_arguments_with_inner(
    frame,
    inner,
    arg_inner_access_reversed,
    execution_ctx,
    num_args_without_rcvr,
):
    arg_i = num_args_without_rcvr - 1
    frame_i = 2
    inner_i = _FRAME_AND_INNER_FIRST_ARG

    while arg_i >= 0:
        if execution_ctx.is_tos_reg_in_use:
            arg_val = execution_ctx.read_stack_elem_tos1(arg_i)
        else:
            arg_val = execution_ctx.read_stack_elem(arg_i)

        if arg_inner_access_reversed[arg_i]:
            inner[inner_i] = arg_val
            inner_i += 1
        else:
            frame[frame_i] = _erase_obj(arg_val)
            frame_i += 1
        arg_i -= 1


@jit.unroll_safe
def stack_pop_old_arguments_and_push_result(execution_ctx, num_args, result):
    if not execution_ctx.is_tos_reg_in_use:
        for _ in range(num_args):
            execution_ctx.stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
        execution_ctx.stack_ptr += 1
        execution_ctx.stack[execution_ctx.stack_ptr] = result
    else:
        execution_ctx.set_tos_tos1(None)
        execution_ctx.pop_1_tos1()

        for _ in range(num_args - 1):
            execution_ctx.set_tos(None)
            execution_ctx.pop_1()
        execution_ctx.push_1(result)

    return execution_ctx.stack_ptr # mostly irrelevant, exists to make rpython happy by returning an int.

@jit.unroll_safe
def get_block_at(frame, ctx_level):
    assert ctx_level > 0

    block = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
    for _ in range(0, ctx_level - 1):
        block = block.get_from_outer(FRAME_AND_INNER_RCVR_IDX)
    return block


@jit.unroll_safe
def get_self_dynamically(frame):
    from som.vmobjects.block_bc import BcBlock
    from som.vmobjects.abstract_object import AbstractObject

    rcvr = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
    assert isinstance(rcvr, AbstractObject)

    while isinstance(rcvr, BcBlock):
        rcvr = rcvr.get_from_outer(FRAME_AND_INNER_RCVR_IDX)
        assert isinstance(rcvr, AbstractObject)

    return rcvr
