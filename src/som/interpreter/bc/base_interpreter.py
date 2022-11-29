from rlib import jit
from rlib.jit import elidable_promote, we_are_jitted
from som.interpreter.ast.frame import read_frame, FRAME_AND_INNER_RCVR_IDX
from som.interpreter.ast.nodes.dispatch import GenericDispatchNode, CachedDispatchNode, INLINE_CACHE_SIZE
from som.interpreter.bc.bytecodes import bytecode_as_str
from som.interpreter.bc.frame import get_self_dynamically, get_block_at
from som.interpreter.control_flow import ReturnException
from som.interpreter.send import lookup_and_send_2, get_clean_inline_cache_and_size, get_inline_cache_size


@jit.unroll_safe
def _do_return_non_local(result, frame, ctx_level):
    # Compute the context for the non-local return
    block = get_block_at(frame, ctx_level)

    # Make sure the block context is still on the stack
    if not block.is_outer_on_stack():
        # Try to recover by sending 'escapedBlock:' to the self object.
        # That is the most outer self object, not the blockSelf.
        self_block = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
        outer_self = get_self_dynamically(frame)
        return lookup_and_send_2(outer_self, self_block, "escapedBlock:")

    raise ReturnException(result, block.get_on_stack_marker())


def _invoke_invokable_slow_path(invokable, num_args, receiver, stack, stack_ptr):
    if num_args == 1:
        stack[stack_ptr] = invokable.invoke_1(receiver)

    elif num_args == 2:
        arg = stack[stack_ptr]
        if we_are_jitted():
            stack[stack_ptr] = None
        stack_ptr -= 1
        stack[stack_ptr] = invokable.invoke_2(receiver, arg)

    elif num_args == 3:
        arg2 = stack[stack_ptr]
        arg1 = stack[stack_ptr - 1]

        if we_are_jitted():
            stack[stack_ptr] = None
            stack[stack_ptr - 1] = None

        stack_ptr -= 2

        stack[stack_ptr] = invokable.invoke_3(receiver, arg1, arg2)

    else:
        stack_ptr = invokable.invoke_n(stack, stack_ptr)
    return stack_ptr


def _unknown_bytecode(bytecode, bytecode_idx, method):
    from som.compiler.bc.disassembler import dump_method

    dump_method(method, "")
    raise Exception(
        "Unknown bytecode: "
        + str(bytecode)
        + " "
        + bytecode_as_str(bytecode)
        + " at bci: "
        + str(bytecode_idx)
    )


def get_self(frame, ctx_level):
    # Get the self object from the interpreter
    if ctx_level == 0:
        return read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
    return get_block_at(frame, ctx_level).get_from_outer(FRAME_AND_INNER_RCVR_IDX)


@elidable_promote("all")
def _lookup(layout, selector, method, bytecode_index, universe):
    cache = first = method.get_inline_cache(bytecode_index)
    while cache is not None:
        if cache.expected_layout is layout:
            return cache
        cache = cache.next_entry

    cache_size = get_inline_cache_size(first)
    if INLINE_CACHE_SIZE >= cache_size:
        invoke = layout.lookup_invokable(selector)
        if invoke is not None:
            new_dispatch_node = CachedDispatchNode(
                rcvr_class=layout, method=invoke, next_entry=first
            )
            method.set_inline_cache(bytecode_index, new_dispatch_node)
            return new_dispatch_node

    return GenericDispatchNode(selector, universe)


def _update_object_and_invalidate_old_caches(obj, method, bytecode_index, universe):
    obj.update_layout_to_match_class()
    obj.get_object_layout(universe)

    old_cache = method.get_inline_cache(bytecode_index)
    method.set_inline_cache(
        bytecode_index, get_clean_inline_cache_and_size(old_cache)[0]
    )


def get_printable_location(bytecode_index, _stack_ptr, method):
    from som.vmobjects.method_bc import BcAbstractMethod

    assert isinstance(method, BcAbstractMethod)
    bc = method.get_bytecode(bytecode_index)
    return "%s @ %d in %s" % (
        bytecode_as_str(bc),
        bytecode_index,
        method.merge_point_string(),
    )


def _not_yet_implemented():
    raise Exception("Not yet implemented")
