from som.interpreter.ast.frame import (
    read_frame,
    write_frame,
    write_inner,
    read_inner,
    FRAME_AND_INNER_RCVR_IDX,
    get_inner_as_context,
)
from som.interpreter.ast.nodes.dispatch import GenericDispatchNode

from som.interpreter.bc.bytecodes import bytecode_length, Bytecodes
from som.interpreter.bc.frame import (
    get_block_at,
    get_self_dynamically,
)
from som.interpreter.bc.interpreter import _unknown_bytecode, get_printable_location, _not_yet_implemented, \
    _update_object_and_invalidate_old_caches, get_self, _lookup, _do_super_send, _do_return_non_local
from som.interpreter.bc.stack_ops import get_tos, push_1, pop_1, read_stack_elem, set_tos, pop_2
from som.interpreter.control_flow import ReturnException
from som.interpreter.send import lookup_and_send_2, lookup_and_send_3
from som.vm.globals import nilObject, trueObject, falseObject
from som.vmobjects.array import Array
from som.vmobjects.block_bc import BcBlock
from som.vmobjects.integer import int_0, int_1

from rlib import jit
from rlib.jit import promote


@jit.unroll_safe
def interpret(method, frame, max_stack_size):
    from som.vm.current import current_universe

    current_bc_idx = 0

    stack_info = {"stack" : [None] * max_stack_size,
                  "stack_ptr": -1,
                  "tos_reg": None,
                  "is_tos_reg_free": False}

    while True:
        jitdriver.jit_merge_point(
            current_bc_idx=current_bc_idx,
            stack_ptr=stack_info["stack_ptr"],
            method=method,
            frame=frame,
            stack=stack_info["stack"],
        )

        bytecode = method.get_bytecode(current_bc_idx)

        # Get the length of the current bytecode
        bc_length = bytecode_length(bytecode)

        # Compute the next bytecode index
        next_bc_idx = current_bc_idx + bc_length

        promote(stack_info["stack_ptr"])

        # Handle the current bytecode
        if bytecode == Bytecodes.halt:
            return get_tos(stack_info)

        if bytecode == Bytecodes.dup:
            push_1(get_tos(stack_info), stack_info)

        elif bytecode == Bytecodes.push_frame:
            push_1(read_frame(frame, method.get_bytecode(current_bc_idx + 1)), stack_info)

        elif bytecode == Bytecodes.push_frame_0:
            push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0), stack_info)

        elif bytecode == Bytecodes.push_frame_1:
            push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1), stack_info)

        elif bytecode == Bytecodes.push_frame_2:
            push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2), stack_info)

        elif bytecode == Bytecodes.push_inner:
            idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)

            if ctx_level == 0:
                push_1(read_inner(frame, idx), stack_info)
            else:
                block = get_block_at(frame, ctx_level)
                push_1(block.get_from_outer(idx), stack_info)

        elif bytecode == Bytecodes.push_inner_0:
            push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0), stack_info)

        elif bytecode == Bytecodes.push_inner_1:
            push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1), stack_info)

        elif bytecode == Bytecodes.push_inner_2:
            push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2), stack_info)

        elif bytecode == Bytecodes.push_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)
            push_1(self_obj.get_field(field_idx), stack_info)

        elif bytecode == Bytecodes.push_field_0:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            push_1(self_obj.get_field(0), stack_info)

        elif bytecode == Bytecodes.push_field_1:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            push_1(self_obj.get_field(1), stack_info)

        elif bytecode == Bytecodes.push_block:
            block_method = method.get_constant(current_bc_idx)
            push_1(BcBlock(block_method, get_inner_as_context(frame)), stack_info)

        elif bytecode == Bytecodes.push_block_no_ctx:
            block_method = method.get_constant(current_bc_idx)
            push_1(BcBlock(block_method, None), stack_info)

        elif bytecode == Bytecodes.push_constant:
            push_1(method.get_constant(current_bc_idx), stack_info)

        elif bytecode == Bytecodes.push_constant_0:
            push_1(method._literals[0], stack_info)  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_1:
            push_1(method._literals[1], stack_info)  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_2:
            push_1(method._literals[2], stack_info)  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_0:
            push_1(int_0, stack_info)

        elif bytecode == Bytecodes.push_1:
            push_1(int_1, stack_info)

        elif bytecode == Bytecodes.push_nil:
            push_1(nilObject, stack_info)

        elif bytecode == Bytecodes.push_global:
            global_name = method.get_constant(current_bc_idx)
            glob = current_universe.get_global(global_name)

            if glob:
                push_1(glob, stack_info)
            else:
                val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                push_1(val, stack_info)

        elif bytecode == Bytecodes.pop:
            pop_1(stack_info)

        elif bytecode == Bytecodes.pop_frame:
            value = pop_1(stack_info)
            write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

        elif bytecode == Bytecodes.pop_frame_0:
            value = pop_1(stack_info)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_frame_1:
            value = pop_1(stack_info)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_frame_2:
            value = pop_1(stack_info)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_inner:
            idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            value = pop_1(stack_info)

            if ctx_level == 0:
                write_inner(frame, idx, value)
            else:
                block = get_block_at(frame, ctx_level)
                block.set_outer(idx, value)

        elif bytecode == Bytecodes.pop_inner_0:
            value = pop_1(stack_info)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_inner_1:
            value = pop_1(stack_info)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_inner_2:
            value = pop_1(stack_info)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            value = pop_1(stack_info)

            self_obj.set_field(field_idx, value)

        elif bytecode == Bytecodes.pop_field_0:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

            value = pop_1(stack_info)

            self_obj.set_field(0, value)

        elif bytecode == Bytecodes.pop_field_1:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

            value = pop_1(stack_info)
            self_obj.set_field(1, value)

        elif bytecode == Bytecodes.send_1:
            signature = method.get_constant(current_bc_idx)
            receiver = get_tos(stack_info)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            set_tos(dispatch_node.dispatch_1(receiver), stack_info)

        elif bytecode == Bytecodes.send_2:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(1, stack_info)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            arg = pop_1(stack_info)
            set_tos(dispatch_node.dispatch_2(receiver, arg), stack_info)

        elif bytecode == Bytecodes.send_3:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(2, stack_info)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, method, current_bc_idx, current_universe
            )

            arg2, arg1 = pop_2(stack_info)
            set_tos(dispatch_node.dispatch_3(receiver, arg1, arg2), stack_info)

        elif bytecode == Bytecodes.send_n:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(signature.get_number_of_signature_arguments() - 1, stack_info)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, method, current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            stack_ptr = dispatch_node.dispatch_n_bc(stack_info, receiver)

        elif bytecode == Bytecodes.super_send:
            stack_ptr = _do_super_send(current_bc_idx, method, stack_info["stack"], stack_info["stack_ptr"])  # TODO needs to handle TOS too

        elif bytecode == Bytecodes.return_local:
            return get_tos(stack_info)

        elif bytecode == Bytecodes.return_non_local:
            val = get_tos(stack_info)
            return _do_return_non_local(val, frame, method.get_bytecode(current_bc_idx + 1))

        elif bytecode == Bytecodes.return_self:
            return read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

        elif bytecode == Bytecodes.return_field_0:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(0)

        elif bytecode == Bytecodes.return_field_1:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(1)

        elif bytecode == Bytecodes.return_field_2:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(2)

        elif bytecode == Bytecodes.inc:
            val = get_tos(stack_info)
            from som.vmobjects.integer import Integer
            from som.vmobjects.double import Double
            from som.vmobjects.biginteger import BigInteger

            if isinstance(val, Integer):
                result = val.prim_inc()
            elif isinstance(val, Double):
                result = val.prim_inc()
            elif isinstance(val, BigInteger):
                result = val.prim_inc()
            else:
                return _not_yet_implemented()
            set_tos(result, stack_info)

        elif bytecode == Bytecodes.dec:
            val = get_tos(stack_info)
            from som.vmobjects.integer import Integer
            from som.vmobjects.double import Double
            from som.vmobjects.biginteger import BigInteger

            if isinstance(val, Integer):
                result = val.prim_dec()
            elif isinstance(val, Double):
                result = val.prim_dec()
            elif isinstance(val, BigInteger):
                result = val.prim_dec()
            else:
                return _not_yet_implemented()
            set_tos(result, stack_info)

        elif bytecode == Bytecodes.inc_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            self_obj.inc_field(field_idx)

        elif bytecode == Bytecodes.inc_field_push:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            stack_ptr += 1
            set_tos(self_obj.inc_field(field_idx), stack_info)

        elif bytecode == Bytecodes.jump:
            next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

        elif bytecode == Bytecodes.jump_on_true_top_nil:
            val = get_tos(stack_info)
            if val is trueObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                set_tos(nilObject, stack_info)
            else:
                pop_1(stack_info)

        elif bytecode == Bytecodes.jump_on_false_top_nil:
            val = get_tos(stack_info)
            if val is falseObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                set_tos(nilObject, stack_info)
            else:
                pop_1(stack_info)

        elif bytecode == Bytecodes.jump_on_true_pop:
            val = get_tos(stack_info)
            if val is trueObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
            pop_1(stack_info)

        elif bytecode == Bytecodes.jump_on_false_pop:
            val = get_tos(stack_info)
            if val is falseObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
            pop_1(stack_info)

        elif bytecode == Bytecodes.jump_backward:
            next_bc_idx = current_bc_idx - method.get_bytecode(current_bc_idx + 1)
            jitdriver.can_enter_jit(
                current_bc_idx=next_bc_idx,
                stack_ptr=stack_ptr,
                method=method,
                frame=frame,
                stack=stack_info["stack"],
            )

        elif bytecode == Bytecodes.jump2:
            next_bc_idx = (
                    current_bc_idx
                    + method.get_bytecode(current_bc_idx + 1)
                    + (method.get_bytecode(current_bc_idx + 2) << 8)
            )

        elif bytecode == Bytecodes.jump2_on_true_top_nil:
            val = get_tos(stack_info)
            if val is trueObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
                set_tos(nilObject, stack_info)
            else:
                pop_1(stack_info)

        elif bytecode == Bytecodes.jump2_on_false_top_nil:
            val = get_tos(stack_info)
            if val is falseObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
                set_tos(nilObject, stack_info)
            else:
                pop_1(stack_info)

        elif bytecode == Bytecodes.jump2_on_true_pop:
            val = get_tos(stack_info)
            if val is trueObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
            pop_1(stack_info)

        elif bytecode == Bytecodes.jump2_on_false_pop:
            val = get_tos(stack_info)
            if val is falseObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
            pop_1(stack_info)

        elif bytecode == Bytecodes.jump2_backward:
            next_bc_idx = current_bc_idx - (
                    method.get_bytecode(current_bc_idx + 1)
                    + (method.get_bytecode(current_bc_idx + 2) << 8)
            )
            jitdriver.can_enter_jit(
                current_bc_idx=next_bc_idx,
                stack_ptr=stack_ptr,
                method=method,
                frame=frame,
                stack=stack_info["stack"],
            )

        elif bytecode == Bytecodes.q_super_send_1:
            invokable = method.get_inline_cache(current_bc_idx)
            set_tos(invokable.dispatch_1(get_tos(stack_info)), stack_info)

        elif bytecode == Bytecodes.q_super_send_2:
            invokable = method.get_inline_cache(current_bc_idx)
            arg = pop_1(stack_info)
            set_tos(invokable.dispatch_2(get_tos(stack_info), arg), stack_info)

        elif bytecode == Bytecodes.q_super_send_3:
            invokable = method.get_inline_cache(current_bc_idx)
            arg2, arg1 = pop_2(stack_info)
            set_tos(invokable.dispatch_3(get_tos(stack_info), arg1, arg2), stack_info)

        elif bytecode == Bytecodes.q_super_send_n:
            invokable = method.get_inline_cache(current_bc_idx)
            stack_ptr = invokable.dispatch_n(stack_info)

        elif bytecode == Bytecodes.push_local:
            method.patch_variable_access(current_bc_idx)
            # retry bytecode after patching
            next_bc_idx = current_bc_idx
        elif bytecode == Bytecodes.push_argument:
            method.patch_variable_access(current_bc_idx)
            # retry bytecode after patching
            next_bc_idx = current_bc_idx
        elif bytecode == Bytecodes.pop_local:
            method.patch_variable_access(current_bc_idx)
            # retry bytecode after patching
            next_bc_idx = current_bc_idx
        elif bytecode == Bytecodes.pop_argument:
            method.patch_variable_access(current_bc_idx)
            # retry bytecode after patching
            next_bc_idx = current_bc_idx
        else:
            _unknown_bytecode(bytecode, current_bc_idx, method)

        current_bc_idx = next_bc_idx


def send_does_not_understand(receiver, selector, stack_info):
    # ignore self
    number_of_arguments = selector.get_number_of_signature_arguments() - 1
    arguments_array = Array.from_size(number_of_arguments)

    # Remove all arguments and put them in the freshly allocated array
    i = number_of_arguments - 1
    while i >= 0:
        value = pop_1(stack_info)
        arguments_array.set_indexable_field(i, value)
        i -= 1

    set_tos(lookup_and_send_3(receiver, selector, arguments_array, "doesNotUnderstand:arguments:"), stack_info)


jitdriver = jit.JitDriver(
    name="Interpreter with TOS caching",
    greens=["current_bc_idx", "method"],
    reds=["stack_ptr", "frame", "stack"],
    # virtualizables=['frame'],
    get_printable_location=get_printable_location,
    # the next line is a workaround around a likely bug in RPython
    # for some reason, the inlining heuristics default to "never inline" when
    # two different jit drivers are involved (in our case, the primitive
    # driver, and this one).
    # the next line says that calls involving this jitdriver should always be
    # inlined once (which means that things like Integer>>< will be inlined
    # into a while loop again, when enabling this drivers).
    should_unroll_one_iteration=lambda current_bc_idx, method: True,
)