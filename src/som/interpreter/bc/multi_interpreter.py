from rlib import jit
from rlib.jit import promote
from som.interpreter.ast.frame import read_frame, FRAME_AND_INNER_RCVR_IDX, read_inner, get_inner_as_context, \
    write_frame, write_inner
from som.interpreter.ast.nodes.dispatch import GenericDispatchNode, CachedDispatchNode
from som.interpreter.bc.bytecodes import bytecode_length, Bytecodes
from som.interpreter.bc.frame import get_block_at, get_self_dynamically
from som.interpreter.bc.stack_states import five, four, two, one, basic, three
from som.interpreter.bc.method_execution_context import MethodExecutionContext
from som.interpreter.bc.base_interpreter import get_printable_location, get_self, _lookup, \
    _update_object_and_invalidate_old_caches, _do_return_non_local, _not_yet_implemented, _unknown_bytecode
from som.interpreter.send import lookup_and_send_2, lookup_and_send_3
from som.vm.globals import nilObject, trueObject, falseObject
from som.vmobjects.array import Array
from som.vmobjects.block_bc import BcBlock
from som.vmobjects.integer import int_1, int_0


def interpret(method, frame, max_stack_size):
    from som.vm.current import current_universe

    execution_ctx = MethodExecutionContext(max_stack_size)

    current_bc_idx = 0

    # if "resolve" in method.get_signature().__str__():
    #     print("bp")

    while True:
        jitdriver.jit_merge_point(
            current_bc_idx=current_bc_idx,
            execution_ctx=execution_ctx,
            stack_ptr=execution_ctx.stack_ptr,
            method=method,
            frame=frame
        )

        bytecode = method.get_bytecode(current_bc_idx)
        cache_state = method.get_cache_state(current_bc_idx)

        # Static info was wrong, bailing out.
        if execution_ctx.state != cache_state:
            execution_ctx.set_state_to_canonical(execution_ctx.state)
            # print("cache miss")
            cache_state = 2
            # execution_ctx.shift_state_to(cache_state)


        # print(bytecode_as_str(bytecode), cache_state)

        # Get the length of the current bytecode
        bc_length = bytecode_length(bytecode)

        # Compute the next bytecode index
        next_bc_idx = current_bc_idx + bc_length

        promote(execution_ctx.stack_ptr)
        if cache_state == 0:
            get_tos = basic.get_tos
            push_1 = basic.push_1
            pop_1 = basic.pop_1
            pop_2 = basic.pop_2
            set_tos = basic.set_tos
            set_tos_minus_1 = basic.set_tos
            set_tos_minus_2 = basic.set_tos
            read_stack_elem = basic.read_stack_elem
        elif cache_state == 1:
            get_tos = one.get_tos
            push_1 = one.push_1
            pop_1 = one.pop_1
            pop_2 = one.pop_2
            set_tos = one.set_tos
            set_tos_minus_1 = basic.set_tos
            set_tos_minus_2 = basic.set_tos
            read_stack_elem = one.read_stack_elem
        elif cache_state == 2:
            get_tos = two.get_tos
            push_1 = two.push_1
            pop_1 = two.pop_1
            pop_2 = two.pop_2
            set_tos = two.set_tos
            set_tos_minus_1 = one.set_tos
            set_tos_minus_2 = basic.set_tos
            read_stack_elem = two.read_stack_elem
        elif cache_state == 3:
            get_tos = three.get_tos
            push_1 = three.push_1
            pop_1 = three.pop_1
            pop_2 = three.pop_2
            set_tos = three.set_tos
            set_tos_minus_1 = two.set_tos
            set_tos_minus_2 = one.set_tos
            read_stack_elem = three.read_stack_elem
        elif cache_state == 4:
            get_tos = four.get_tos
            push_1 = four.push_1
            pop_1 = four.pop_1
            pop_2 = four.pop_2
            set_tos = four.set_tos
            set_tos_minus_1 = three.set_tos
            set_tos_minus_2 = two.set_tos
            read_stack_elem = four.read_stack_elem
        else:
            get_tos = five.get_tos
            push_1 = five.push_1
            pop_1 = five.pop_1
            pop_2 = five.pop_2
            set_tos = five.set_tos
            set_tos_minus_1 = four.set_tos
            set_tos_minus_2 = three.set_tos
            read_stack_elem = five.read_stack_elem

        if bytecode == Bytecodes.halt:
            return get_tos(execution_ctx)

        if bytecode == Bytecodes.dup:
            push_1(execution_ctx, get_tos(execution_ctx))

        elif bytecode == Bytecodes.push_frame:
            push_1(execution_ctx, read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

        elif bytecode == Bytecodes.push_frame_0:
            push_1(execution_ctx, read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

        elif bytecode == Bytecodes.push_frame_1:
            push_1(execution_ctx, read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

        elif bytecode == Bytecodes.push_frame_2:
            push_1(execution_ctx, read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

        elif bytecode == Bytecodes.push_inner:
            idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)

            if ctx_level == 0:
                push_1(execution_ctx, read_inner(frame, idx))
            else:
                block = get_block_at(frame, ctx_level)
                push_1(execution_ctx, block.get_from_outer(idx))

        elif bytecode == Bytecodes.push_inner_0:
            push_1(execution_ctx, read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

        elif bytecode == Bytecodes.push_inner_1:
            push_1(execution_ctx, read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

        elif bytecode == Bytecodes.push_inner_2:
            push_1(execution_ctx, read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

        elif bytecode == Bytecodes.push_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)
            push_1(execution_ctx, self_obj.get_field(field_idx))

        elif bytecode == Bytecodes.push_field_0:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            push_1(execution_ctx, self_obj.get_field(0))

        elif bytecode == Bytecodes.push_field_1:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
            push_1(execution_ctx, self_obj.get_field(1))

        elif bytecode == Bytecodes.push_block:
            block_method = method.get_constant(current_bc_idx)
            push_1(execution_ctx, BcBlock(block_method, get_inner_as_context(frame)))

        elif bytecode == Bytecodes.push_block_no_ctx:
            block_method = method.get_constant(current_bc_idx)
            push_1(execution_ctx, BcBlock(block_method, None))

        elif bytecode == Bytecodes.push_constant:
            push_1(execution_ctx, method.get_constant(current_bc_idx))

        elif bytecode == Bytecodes.push_constant_0:
            push_1(execution_ctx, method._literals[0])  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_1:
            push_1(execution_ctx, method._literals[1])  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_2:
            push_1(execution_ctx, method._literals[2])  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_0:
            push_1(execution_ctx, int_0)

        elif bytecode == Bytecodes.push_1:
            push_1(execution_ctx, int_1)

        elif bytecode == Bytecodes.push_nil:
            push_1(execution_ctx, nilObject)

        elif bytecode == Bytecodes.push_global:
            global_name = method.get_constant(current_bc_idx)
            glob = current_universe.get_global(global_name)

            if glob:
                push_1(execution_ctx, glob)
            else:
                val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                push_1(execution_ctx, val)

        elif bytecode == Bytecodes.pop:
            pop_1(execution_ctx)

        elif bytecode == Bytecodes.pop_frame:
            value = pop_1(execution_ctx)
            write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

        elif bytecode == Bytecodes.pop_frame_0:
            value = pop_1(execution_ctx)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_frame_1:
            value = pop_1(execution_ctx)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_frame_2:
            value = pop_1(execution_ctx)
            write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_inner:
            idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            value = pop_1(execution_ctx)

            if ctx_level == 0:
                write_inner(frame, idx, value)
            else:
                block = get_block_at(frame, ctx_level)
                block.set_outer(idx, value)

        elif bytecode == Bytecodes.pop_inner_0:
            value = pop_1(execution_ctx)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_inner_1:
            value = pop_1(execution_ctx)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_inner_2:
            value = pop_1(execution_ctx)
            write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            value = pop_1(execution_ctx)

            self_obj.set_field(field_idx, value)

        elif bytecode == Bytecodes.pop_field_0:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

            value = pop_1(execution_ctx)

            self_obj.set_field(0, value)

        elif bytecode == Bytecodes.pop_field_1:
            self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

            value = pop_1(execution_ctx)
            self_obj.set_field(1, value)

        elif bytecode == Bytecodes.send_1:
            signature = method.get_constant(current_bc_idx)
            receiver = get_tos(execution_ctx)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            set_tos(execution_ctx, dispatch_node.dispatch_1(receiver))

        elif bytecode == Bytecodes.send_2:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(execution_ctx, 1)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            arg = pop_1(execution_ctx)
            set_tos_minus_1(execution_ctx, dispatch_node.dispatch_2(receiver, arg))

        elif bytecode == Bytecodes.send_3:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(execution_ctx, 2)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, method, current_bc_idx, current_universe
            )

            arg2, arg1 = pop_2(execution_ctx)
            set_tos_minus_2(execution_ctx, dispatch_node.dispatch_3(receiver, arg1, arg2))

        elif bytecode == Bytecodes.send_n:
            signature = method.get_constant(current_bc_idx)
            receiver = read_stack_elem(execution_ctx, signature.get_number_of_signature_arguments() - 1)

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, method, current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, method, current_bc_idx, current_universe
                )

            dispatch_node.dispatch_n_bc(execution_ctx, receiver)

        elif bytecode == Bytecodes.super_send:
            _do_super_send(current_bc_idx, method, execution_ctx)

        elif bytecode == Bytecodes.return_local:
            return get_tos(execution_ctx)

        elif bytecode == Bytecodes.return_non_local:
            val = get_tos(execution_ctx)
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
            val = get_tos(execution_ctx)
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
            set_tos(execution_ctx, result)

        elif bytecode == Bytecodes.dec:
            val = get_tos(execution_ctx)
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
            set_tos(execution_ctx, result)

        elif bytecode == Bytecodes.inc_field:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            self_obj.inc_field(field_idx)

        elif bytecode == Bytecodes.inc_field_push:
            field_idx = method.get_bytecode(current_bc_idx + 1)
            ctx_level = method.get_bytecode(current_bc_idx + 2)
            self_obj = get_self(frame, ctx_level)

            push_1(execution_ctx, self_obj.inc_field(field_idx))

        elif bytecode == Bytecodes.jump:
            next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

        elif bytecode == Bytecodes.jump_on_true_top_nil:
            val = get_tos(execution_ctx)
            if val is trueObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                set_tos(execution_ctx, nilObject)
            else:
                pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump_on_false_top_nil:
            val = get_tos(execution_ctx)
            if val is falseObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                set_tos(execution_ctx, nilObject)
            else:
                pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump_on_true_pop:
            val = get_tos(execution_ctx)
            if val is trueObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
            pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump_on_false_pop:
            val = get_tos(execution_ctx)
            if val is falseObject:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
            pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump_backward:
            next_bc_idx = current_bc_idx - method.get_bytecode(current_bc_idx + 1)
            jitdriver.can_enter_jit(
                current_bc_idx=next_bc_idx,
                execution_ctx=execution_ctx,
                stack_ptr=execution_ctx.stack_ptr,
                method=method,
                frame=frame,
            )

        elif bytecode == Bytecodes.jump2:
            next_bc_idx = (
                    current_bc_idx
                    + method.get_bytecode(current_bc_idx + 1)
                    + (method.get_bytecode(current_bc_idx + 2) << 8)
            )

        elif bytecode == Bytecodes.jump2_on_true_top_nil:
            val = get_tos(execution_ctx)
            if val is trueObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
                set_tos(execution_ctx, nilObject)
            else:
                pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump2_on_false_top_nil:
            val = get_tos(execution_ctx)
            if val is falseObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
                set_tos(execution_ctx, nilObject)
            else:
                pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump2_on_true_pop:
            val = get_tos(execution_ctx)
            if val is trueObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
            pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump2_on_false_pop:
            val = get_tos(execution_ctx)
            if val is falseObject:
                next_bc_idx = (
                        current_bc_idx
                        + method.get_bytecode(current_bc_idx + 1)
                        + (method.get_bytecode(current_bc_idx + 2) << 8)
                )
            pop_1(execution_ctx)

        elif bytecode == Bytecodes.jump2_backward:
            next_bc_idx = current_bc_idx - (
                    method.get_bytecode(current_bc_idx + 1)
                    + (method.get_bytecode(current_bc_idx + 2) << 8)
            )
            jitdriver.can_enter_jit(
                current_bc_idx=next_bc_idx,
                execution_ctx=execution_ctx,
                stack_ptr=execution_ctx.stack_ptr,
                method=method,
                frame=frame
            )

        elif bytecode == Bytecodes.q_super_send_1:
            invokable = method.get_inline_cache(current_bc_idx)
            execution_ctx.set_tos_any(invokable.dispatch_1(execution_ctx.get_tos_any()))

        elif bytecode == Bytecodes.q_super_send_2:
            invokable = method.get_inline_cache(current_bc_idx)
            arg = pop_1(execution_ctx)
            execution_ctx.set_tos_any(invokable.dispatch_2(execution_ctx.get_tos_any(), arg))

        elif bytecode == Bytecodes.q_super_send_3:
            invokable = method.get_inline_cache(current_bc_idx)
            arg2, arg1 = pop_2(execution_ctx)
            execution_ctx.set_tos_any(invokable.dispatch_3(execution_ctx.get_tos_any(), arg1, arg2))

        elif bytecode == Bytecodes.q_super_send_n:
            invokable = method.get_inline_cache(current_bc_idx)
            invokable.dispatch_n_bc(execution_ctx, None)

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

def _do_super_send(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_any_state(num_args - 1)

    if invokable:
        first = method.get_inline_cache(bytecode_index)
        method.set_inline_cache(
            bytecode_index,
            CachedDispatchNode(
                receiver_class.get_layout_for_instances(), invokable, first
            ),
        )
        if num_args == 1:
            bc = Bytecodes.q_super_send_1
        elif num_args == 2:
            bc = Bytecodes.q_super_send_2
        elif num_args == 3:
            bc = Bytecodes.q_super_send_3
        else:
            bc = Bytecodes.q_super_send_n
        method.set_bytecode(bytecode_index, bc)

        if num_args == 1:
            execution_ctx.set_tos_any(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_any()
            execution_ctx.set_tos_any(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2 = execution_ctx.pop_1_any()
            arg1 = execution_ctx.pop_1_any()
            execution_ctx.set_tos_any(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )

def send_does_not_understand(receiver, selector, execution_ctx):
    # ignore self
    number_of_arguments = selector.get_number_of_signature_arguments() - 1
    arguments_array = Array.from_size(number_of_arguments)

    # Remove all arguments and put them in the freshly allocated array
    i = number_of_arguments - 1
    while i >= 0:
        value = execution_ctx.pop_1_any()
        arguments_array.set_indexable_field(i, value)
        i -= 1

    # in practice since it's a send with three args, it'll always reduce the state by 3.
    # so some of the following checks are redundant but amenable to adding more states.
    dnu_ret = lookup_and_send_3(receiver, selector, arguments_array, "doesNotUnderstand:arguments:")
    execution_ctx.set_tos_any(dnu_ret)

    return execution_ctx.stack_ptr


jitdriver = jit.JitDriver(
        name="Interpreter",
        greens=["current_bc_idx", "stack_ptr", "method"],
        reds=["execution_ctx", "frame"],
        # virtualizables=['frame'],
        get_printable_location=get_printable_location,
        # the next line is a workaround around a likely bug in RPython
        # for some reason, the inlining heuristics default to "never inline" when
        # two different jit drivers are involved (in our case, the primitive
        # driver, and this one).
        # the next line says that calls involving this jitdriver should always be
        # inlined once (which means that things like Integer>>< will be inlined
        # into a while loop again, when enabling this drivers).
        should_unroll_one_iteration=lambda current_bc_idx, stack_ptr, method: True,
    )
