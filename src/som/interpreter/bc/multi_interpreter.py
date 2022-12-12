from rlib import jit
from rlib.jit import promote, we_are_jitted
from som.interpreter.ast.frame import read_frame, FRAME_AND_INNER_RCVR_IDX, read_inner, get_inner_as_context, \
    write_frame, write_inner
from som.interpreter.ast.nodes.dispatch import GenericDispatchNode, CachedDispatchNode
from som.interpreter.bc.bytecodes import bytecode_length, Bytecodes, bytecode_as_str
from som.interpreter.bc.frame import get_block_at, get_self_dynamically
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

    # print(method.get_signature())
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

        # Get the length of the current bytecode
        bc_length = bytecode_length(bytecode)

        # Compute the next bytecode index
        next_bc_idx = current_bc_idx + bc_length

        promote(execution_ctx.stack_ptr)

        if execution_ctx.state == 0:
            # print "BASE ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1(execution_ctx.get_tos())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1()
                execution_ctx.set_tos(dispatch_node.dispatch_2(receiver, arg))

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2()
                execution_ctx.set_tos(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem(signature.get_number_of_signature_arguments() - 1)

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
                return execution_ctx.get_tos()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos()
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
                val = execution_ctx.get_tos()
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
                execution_ctx.set_tos(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos()
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
                execution_ctx.set_tos(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos(nilObject)
                else:
                    execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos(nilObject)
                else:
                    execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1()

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
                val = execution_ctx.get_tos()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos(nilObject)
                else:
                    execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos(nilObject)
                else:
                    execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1()

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
                execution_ctx.set_tos(invokable.dispatch_1(execution_ctx.get_tos()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1()
                execution_ctx.set_tos(invokable.dispatch_2(execution_ctx.get_tos(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2()
                execution_ctx.set_tos(invokable.dispatch_3(execution_ctx.get_tos(), arg1, arg2))

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

        elif execution_ctx.state == 1:
            # print "TOS1 ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos_tos1()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1_tos1(execution_ctx.get_tos_tos1())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1_tos1(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1_tos1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1_tos1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1_tos1(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1_tos1(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1_tos1(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1_tos1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1_tos1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1_tos1(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1_tos1(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos1(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos1(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos1(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos1(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1_tos1(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1_tos1(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1_tos1(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1_tos1(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1_tos1(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1_tos1(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1_tos1(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1_tos1(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1_tos1(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1_tos1()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1_tos1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1_tos1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1_tos1()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1_tos1()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1_tos1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1_tos1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1_tos1()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1_tos1()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos1()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos1()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos_tos1()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos_tos1(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos1(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1_tos1()
                execution_ctx.set_tos(dispatch_node.dispatch_2(receiver, arg))

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos1(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2_tos1()
                execution_ctx.set_tos(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos1(signature.get_number_of_signature_arguments() - 1)

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
                _do_super_send_tos1(current_bc_idx, method, execution_ctx)

            elif bytecode == Bytecodes.return_local:
                return execution_ctx.get_tos_tos1()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos_tos1()
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
                val = execution_ctx.get_tos_tos1()
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
                execution_ctx.set_tos_tos1(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos_tos1()
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
                execution_ctx.set_tos_tos1(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1_tos1(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos_tos1()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos1(nilObject)
                else:
                    execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos_tos1()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos1(nilObject)
                else:
                    execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos_tos1()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos_tos1()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos1()

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
                val = execution_ctx.get_tos_tos1()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos1(nilObject)
                else:
                    execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos_tos1()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos1(nilObject)
                else:
                    execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos_tos1()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos1()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos_tos1()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos1()

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
                execution_ctx.set_tos_tos1(invokable.dispatch_1(execution_ctx.get_tos_tos1()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1_tos1()
                execution_ctx.set_tos_tos1(invokable.dispatch_2(execution_ctx.get_tos(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2_tos1()
                execution_ctx.set_tos_tos1(invokable.dispatch_3(execution_ctx.get_tos(), arg1, arg2))

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
        elif execution_ctx.state == 2:
            # print "TOS2 ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos_tos2()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1_tos2(execution_ctx.get_tos_tos2())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1_tos2(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1_tos2(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1_tos2(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1_tos2(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1_tos2(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1_tos2(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1_tos2(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1_tos2(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1_tos2(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1_tos2(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos2(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos2(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos2(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos2(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1_tos2(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1_tos2(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1_tos2(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1_tos2(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1_tos2(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1_tos2(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1_tos2(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1_tos2(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1_tos2(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1_tos2()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1_tos2()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1_tos2()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1_tos2()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1_tos2()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1_tos2()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1_tos2()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1_tos2()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1_tos2()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos2()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos2()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos_tos2()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos_tos2(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos2(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1_tos2()
                val = dispatch_node.dispatch_2(receiver, arg)
                execution_ctx.set_tos_tos1(val)

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos2(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2_tos2()
                execution_ctx.set_tos(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos2(signature.get_number_of_signature_arguments() - 1)

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
                _do_super_send_tos2(current_bc_idx, method, execution_ctx)

            elif bytecode == Bytecodes.return_local:
                return execution_ctx.get_tos_tos2()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos_tos2()
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
                val = execution_ctx.get_tos_tos2()
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
                execution_ctx.set_tos_tos2(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos_tos2()
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
                execution_ctx.set_tos_tos2(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1_tos2(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos_tos2()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos2(nilObject)
                else:
                    execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos_tos2()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos2(nilObject)
                else:
                    execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos_tos2()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos_tos2()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos2()

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
                val = execution_ctx.get_tos_tos2()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos2(nilObject)
                else:
                    execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos_tos2()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos2(nilObject)
                else:
                    execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos_tos2()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos2()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos_tos2()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos2()

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
                execution_ctx.set_tos_tos2(invokable.dispatch_1(execution_ctx.get_tos_tos2()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1_tos2()
                execution_ctx.set_tos_tos1(invokable.dispatch_2(execution_ctx.get_tos_tos1(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2_tos2()
                execution_ctx.set_tos(invokable.dispatch_3(execution_ctx.get_tos(), arg1, arg2))

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
        elif execution_ctx.state == 3:
            # print "TOS3 ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos_tos3()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1_tos3(execution_ctx.get_tos_tos3())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1_tos3(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1_tos3(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1_tos3(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1_tos3(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1_tos3(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1_tos3(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1_tos3(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1_tos3(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1_tos3(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1_tos3(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos3(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos3(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos3(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos3(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1_tos3(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1_tos3(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1_tos3(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1_tos3(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1_tos3(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1_tos3(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1_tos3(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1_tos3(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1_tos3(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1_tos3()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1_tos3()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1_tos3()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1_tos3()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1_tos3()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1_tos3()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1_tos3()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1_tos3()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1_tos3()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos3()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos3()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos_tos3()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos_tos3(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos3(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1_tos3()
                val = dispatch_node.dispatch_2(receiver, arg)
                execution_ctx.set_tos_tos2(val)

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos3(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2_tos3()
                execution_ctx.set_tos_tos1(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos3(signature.get_number_of_signature_arguments() - 1)

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
                _do_super_send_tos3(current_bc_idx, method, execution_ctx)

            elif bytecode == Bytecodes.return_local:
                return execution_ctx.get_tos_tos3()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos_tos3()
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
                val = execution_ctx.get_tos_tos3()
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
                execution_ctx.set_tos_tos3(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos_tos3()
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
                execution_ctx.set_tos_tos3(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1_tos3(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos_tos3()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos3(nilObject)
                else:
                    execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos_tos3()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos3(nilObject)
                else:
                    execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos_tos3()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos_tos3()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos3()

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
                val = execution_ctx.get_tos_tos3()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos3(nilObject)
                else:
                    execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos_tos3()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos3(nilObject)
                else:
                    execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos_tos3()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos3()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos_tos3()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos3()

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
                execution_ctx.set_tos_tos3(invokable.dispatch_1(execution_ctx.get_tos_tos3()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1_tos3()
                execution_ctx.set_tos_tos1(invokable.dispatch_2(execution_ctx.get_tos_tos2(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2_tos3()
                execution_ctx.set_tos(invokable.dispatch_3(execution_ctx.get_tos_tos1(), arg1, arg2))

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
        elif execution_ctx.state == 4:
            # print "TOS4 ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos_tos4()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1_tos4(execution_ctx.get_tos_tos4())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1_tos4(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1_tos4(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1_tos4(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1_tos4(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1_tos4(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1_tos4(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1_tos4(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1_tos4(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1_tos4(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1_tos4(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos4(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos4(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos4(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos4(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1_tos4(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1_tos4(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1_tos4(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1_tos4(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1_tos4(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1_tos4(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1_tos4(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1_tos4(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1_tos4(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1_tos4()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1_tos4()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1_tos4()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1_tos4()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1_tos4()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1_tos4()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1_tos4()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1_tos4()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1_tos4()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos4()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos4()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos_tos4()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos_tos4(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos4(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1_tos4()
                val = dispatch_node.dispatch_2(receiver, arg)
                execution_ctx.set_tos_tos3(val)

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos4(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2_tos4()
                execution_ctx.set_tos_tos2(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos4(signature.get_number_of_signature_arguments() - 1)

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
                _do_super_send_tos4(current_bc_idx, method, execution_ctx)

            elif bytecode == Bytecodes.return_local:
                return execution_ctx.get_tos_tos4()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos_tos4()
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
                val = execution_ctx.get_tos_tos4()
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
                execution_ctx.set_tos_tos4(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos_tos4()
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
                execution_ctx.set_tos_tos4(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1_tos4(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos_tos4()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos4(nilObject)
                else:
                    execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos_tos4()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos4(nilObject)
                else:
                    execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos_tos4()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos_tos4()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos4()

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
                val = execution_ctx.get_tos_tos4()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos4(nilObject)
                else:
                    execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos_tos4()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos4(nilObject)
                else:
                    execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos_tos4()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos4()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos_tos4()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos4()

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
                execution_ctx.set_tos_tos4(invokable.dispatch_1(execution_ctx.get_tos_tos4()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1_tos4()
                execution_ctx.set_tos_tos1(invokable.dispatch_2(execution_ctx.get_tos_tos3(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2_tos4()
                execution_ctx.set_tos(invokable.dispatch_3(execution_ctx.get_tos_tos2(), arg1, arg2))

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
        elif execution_ctx.state == 5:
            # print "TOS5 ", bytecode_as_str(bytecode)

            if bytecode == Bytecodes.halt:
                return execution_ctx.get_tos_tos5()

            if bytecode == Bytecodes.dup:
                execution_ctx.push_1_tos5(execution_ctx.get_tos_tos5())

            elif bytecode == Bytecodes.push_frame:
                execution_ctx.push_1_tos5(read_frame(frame, method.get_bytecode(current_bc_idx + 1)))

            elif bytecode == Bytecodes.push_frame_0:
                execution_ctx.push_1_tos5(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_frame_1:
                execution_ctx.push_1_tos5(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_frame_2:
                execution_ctx.push_1_tos5(read_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)

                if ctx_level == 0:
                    execution_ctx.push_1_tos5(read_inner(frame, idx))
                else:
                    block = get_block_at(frame, ctx_level)
                    execution_ctx.push_1_tos5(block.get_from_outer(idx))

            elif bytecode == Bytecodes.push_inner_0:
                execution_ctx.push_1_tos5(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0))

            elif bytecode == Bytecodes.push_inner_1:
                execution_ctx.push_1_tos5(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1))

            elif bytecode == Bytecodes.push_inner_2:
                execution_ctx.push_1_tos5(read_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2))

            elif bytecode == Bytecodes.push_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)
                execution_ctx.push_1_tos5(self_obj.get_field(field_idx))

            elif bytecode == Bytecodes.push_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos5(self_obj.get_field(0))

            elif bytecode == Bytecodes.push_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)
                execution_ctx.push_1_tos5(self_obj.get_field(1))

            elif bytecode == Bytecodes.push_block:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos5(BcBlock(block_method, get_inner_as_context(frame)))

            elif bytecode == Bytecodes.push_block_no_ctx:
                block_method = method.get_constant(current_bc_idx)
                execution_ctx.push_1_tos5(BcBlock(block_method, None))

            elif bytecode == Bytecodes.push_constant:
                execution_ctx.push_1_tos5(method.get_constant(current_bc_idx))

            elif bytecode == Bytecodes.push_constant_0:
                execution_ctx.push_1_tos5(method._literals[0])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_1:
                execution_ctx.push_1_tos5(method._literals[1])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_constant_2:
                execution_ctx.push_1_tos5(method._literals[2])  # pylint: disable=protected-access

            elif bytecode == Bytecodes.push_0:
                execution_ctx.push_1_tos5(int_0)

            elif bytecode == Bytecodes.push_1:
                execution_ctx.push_1_tos5(int_1)

            elif bytecode == Bytecodes.push_nil:
                execution_ctx.push_1_tos5(nilObject)

            elif bytecode == Bytecodes.push_global:
                global_name = method.get_constant(current_bc_idx)
                glob = current_universe.get_global(global_name)

                if glob:
                    execution_ctx.push_1_tos5(glob)
                else:
                    val = lookup_and_send_2(get_self_dynamically(frame), global_name, "unknownGlobal:")
                    execution_ctx.push_1_tos5(val)

            elif bytecode == Bytecodes.pop:
                execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.pop_frame:
                value = execution_ctx.pop_1_tos5()
                write_frame(frame, method.get_bytecode(current_bc_idx + 1), value)

            elif bytecode == Bytecodes.pop_frame_0:
                value = execution_ctx.pop_1_tos5()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_frame_1:
                value = execution_ctx.pop_1_tos5()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_frame_2:
                value = execution_ctx.pop_1_tos5()
                write_frame(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_inner:
                idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                value = execution_ctx.pop_1_tos5()

                if ctx_level == 0:
                    write_inner(frame, idx, value)
                else:
                    block = get_block_at(frame, ctx_level)
                    block.set_outer(idx, value)

            elif bytecode == Bytecodes.pop_inner_0:
                value = execution_ctx.pop_1_tos5()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

            elif bytecode == Bytecodes.pop_inner_1:
                value = execution_ctx.pop_1_tos5()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

            elif bytecode == Bytecodes.pop_inner_2:
                value = execution_ctx.pop_1_tos5()
                write_inner(frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

            elif bytecode == Bytecodes.pop_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                value = execution_ctx.pop_1_tos5()

                self_obj.set_field(field_idx, value)

            elif bytecode == Bytecodes.pop_field_0:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos5()

                self_obj.set_field(0, value)

            elif bytecode == Bytecodes.pop_field_1:
                self_obj = read_frame(frame, FRAME_AND_INNER_RCVR_IDX)

                value = execution_ctx.pop_1_tos5()
                self_obj.set_field(1, value)

            elif bytecode == Bytecodes.send_1:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.get_tos_tos5()

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                execution_ctx.set_tos_tos5(dispatch_node.dispatch_1(receiver))

            elif bytecode == Bytecodes.send_2:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos5(1)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(layout, signature, method, current_bc_idx, current_universe)

                if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                    _update_object_and_invalidate_old_caches(
                        receiver, method, current_bc_idx, current_universe
                    )

                arg = execution_ctx.pop_1_tos5()
                val = dispatch_node.dispatch_2(receiver, arg)
                execution_ctx.set_tos_tos4(val)

            elif bytecode == Bytecodes.send_3:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos5(2)

                layout = receiver.get_object_layout(current_universe)
                dispatch_node = _lookup(
                    layout, signature, method, current_bc_idx, current_universe
                )

                arg2, arg1 = execution_ctx.pop_2_tos5()
                execution_ctx.set_tos_tos3(dispatch_node.dispatch_3(receiver, arg1, arg2))

            elif bytecode == Bytecodes.send_n:
                signature = method.get_constant(current_bc_idx)
                receiver = execution_ctx.read_stack_elem_tos5(signature.get_number_of_signature_arguments() - 1)

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
                _do_super_send_tos5(current_bc_idx, method, execution_ctx)

            elif bytecode == Bytecodes.return_local:
                return execution_ctx.get_tos_tos5()

            elif bytecode == Bytecodes.return_non_local:
                val = execution_ctx.get_tos_tos5()
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
                val = execution_ctx.get_tos_tos5()
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
                execution_ctx.set_tos_tos5(result)

            elif bytecode == Bytecodes.dec:
                val = execution_ctx.get_tos_tos5()
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
                execution_ctx.set_tos_tos5(result)

            elif bytecode == Bytecodes.inc_field:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                self_obj.inc_field(field_idx)

            elif bytecode == Bytecodes.inc_field_push:
                field_idx = method.get_bytecode(current_bc_idx + 1)
                ctx_level = method.get_bytecode(current_bc_idx + 2)
                self_obj = get_self(frame, ctx_level)

                execution_ctx.push_1_tos5(self_obj.inc_field(field_idx))

            elif bytecode == Bytecodes.jump:
                next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)

            elif bytecode == Bytecodes.jump_on_true_top_nil:
                val = execution_ctx.get_tos_tos5()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos5(nilObject)
                else:
                    execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump_on_false_top_nil:
                val = execution_ctx.get_tos_tos5()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                    execution_ctx.set_tos_tos5(nilObject)
                else:
                    execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump_on_true_pop:
                val = execution_ctx.get_tos_tos5()
                if val is trueObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump_on_false_pop:
                val = execution_ctx.get_tos_tos5()
                if val is falseObject:
                    next_bc_idx = current_bc_idx + method.get_bytecode(current_bc_idx + 1)
                execution_ctx.pop_1_tos5()

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
                val = execution_ctx.get_tos_tos5()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos5(nilObject)
                else:
                    execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump2_on_false_top_nil:
                val = execution_ctx.get_tos_tos5()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                    execution_ctx.set_tos_tos5(nilObject)
                else:
                    execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump2_on_true_pop:
                val = execution_ctx.get_tos_tos5()
                if val is trueObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos5()

            elif bytecode == Bytecodes.jump2_on_false_pop:
                val = execution_ctx.get_tos_tos5()
                if val is falseObject:
                    next_bc_idx = (
                            current_bc_idx
                            + method.get_bytecode(current_bc_idx + 1)
                            + (method.get_bytecode(current_bc_idx + 2) << 8)
                    )
                execution_ctx.pop_1_tos5()

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
                execution_ctx.set_tos_tos5(invokable.dispatch_1(execution_ctx.get_tos_tos5()))

            elif bytecode == Bytecodes.q_super_send_2:
                invokable = method.get_inline_cache(current_bc_idx)
                arg = execution_ctx.pop_1_tos5()
                execution_ctx.set_tos_tos1(invokable.dispatch_2(execution_ctx.get_tos_tos4(), arg))

            elif bytecode == Bytecodes.q_super_send_3:
                invokable = method.get_inline_cache(current_bc_idx)
                arg2, arg1 = execution_ctx.pop_2_tos5()
                execution_ctx.set_tos(invokable.dispatch_3(execution_ctx.get_tos_tos3(), arg1, arg2))

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
    receiver = execution_ctx.read_stack_elem(num_args - 1)

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
            execution_ctx.set_tos(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1()
            execution_ctx.set_tos(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2()
            execution_ctx.set_tos(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )


def _do_super_send_tos1(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_tos1(num_args - 1)

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
            execution_ctx.set_tos_tos1(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_tos1()
            execution_ctx.set_tos(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2_tos1()
            execution_ctx.set_tos(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )


def _do_super_send_tos2(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_tos2(num_args - 1)

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
            execution_ctx.set_tos_tos2(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_tos2()
            execution_ctx.set_tos_tos1(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2_tos2()
            execution_ctx.set_tos(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )

def _do_super_send_tos3(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_tos3(num_args - 1)

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
            execution_ctx.set_tos_tos3(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_tos3()
            execution_ctx.set_tos_tos2(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2_tos3()
            execution_ctx.set_tos_tos1(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )

def _do_super_send_tos4(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_tos4(num_args - 1)

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
            execution_ctx.set_tos_tos4(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_tos4()
            execution_ctx.set_tos_tos3(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2_tos4()
            execution_ctx.set_tos_tos2(invokable.invoke_3(receiver, arg1, arg2))

        else:
            invokable.invoke_n(execution_ctx)
    else:
        send_does_not_understand(
            receiver, invokable.get_signature(), execution_ctx
        )

def _do_super_send_tos5(bytecode_index, method, execution_ctx):
    signature = method.get_constant(bytecode_index)

    receiver_class = method.get_holder().get_super_class()
    invokable = receiver_class.lookup_invokable(signature)

    num_args = invokable.get_number_of_signature_arguments()
    receiver = execution_ctx.read_stack_elem_tos5(num_args - 1)

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
            execution_ctx.set_tos_tos5(invokable.invoke_1(receiver))

        elif num_args == 2:
            arg = execution_ctx.pop_1_tos5()
            execution_ctx.set_tos_tos4(invokable.invoke_2(receiver, arg))

        elif num_args == 3:
            arg2, arg1 = execution_ctx.pop_2_tos5()
            execution_ctx.set_tos_tos3(invokable.invoke_3(receiver, arg1, arg2))

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
    if execution_ctx.state == 0:
        execution_ctx.set_tos(dnu_ret)
    elif execution_ctx.state == 1:
        execution_ctx.set_tos_tos1(dnu_ret)
    elif execution_ctx.state == 2:
        execution_ctx.set_tos_tos2(dnu_ret)
    elif execution_ctx.state == 3:
        execution_ctx.set_tos_tos3(dnu_ret)
    elif execution_ctx.state == 4:
        execution_ctx.set_tos_tos4(dnu_ret)
    elif execution_ctx.state == 5:
        execution_ctx.set_tos_tos5(dnu_ret)

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
