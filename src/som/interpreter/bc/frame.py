from rlib import jit
from rlib.debug import make_sure_not_resized
from som.interpreter.bc.stack_ops import push_1, pop_1, read_stack_elem, set_tos

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
    prev_stack_info,
    num_args,
):
    frame = [_erase_obj(nilObject)] * size_frame
    make_sure_not_resized(frame)

    receiver = read_stack_elem(num_args - 1, prev_stack_info)
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
            prev_stack_info,
            num_args - 1,
        )
    else:
        frame[0] = _erase_list(None)
        frame[FRAME_AND_INNER_RCVR_IDX] = _erase_obj(receiver)
        _set_arguments_without_inner(frame, prev_stack_info, num_args - 1)

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
    frame, prev_stack_info, num_args_without_rcvr
):
    arg_i = num_args_without_rcvr - 1
    frame_i = _FRAME_AND_INNER_FIRST_ARG

    while arg_i >= 0:
        frame[frame_i] = _erase_obj(read_stack_elem(arg_i, prev_stack_info))
        frame_i += 1
        arg_i -= 1


@jit.unroll_safe
def _set_arguments_with_inner(
    frame,
    inner,
    arg_inner_access_reversed,
    prev_stack_info,
    num_args_without_rcvr,
):
    arg_i = num_args_without_rcvr - 1
    frame_i = 2
    inner_i = _FRAME_AND_INNER_FIRST_ARG

    while arg_i >= 0:
        arg_val = read_stack_elem(arg_i, prev_stack_info)
        if arg_inner_access_reversed[arg_i]:
            inner[inner_i] = arg_val
            inner_i += 1
        else:
            frame[frame_i] = _erase_obj(arg_val)
            frame_i += 1
        arg_i -= 1


@jit.unroll_safe
def stack_pop_old_arguments_and_push_result(stack_info, num_args, result):
    for _ in range(num_args):
        set_tos(None, stack_info)
        pop_1(stack_info)
    push_1(result, stack_info)


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
