from som.interpreter.ast.frame import (
    read_frame,
    write_frame,
    write_inner,
    read_inner,
    FRAME_AND_INNER_RCVR_IDX,
    get_inner_as_context,
)
from som.interpreter.ast.nodes.dispatch import (
    CachedDispatchNode,
    INLINE_CACHE_SIZE,
    GenericDispatchNode,
)
from som.interpreter.bc.base_interpreter import get_printable_location, _lookup, _invoke_invokable_slow_path, get_self, \
    _update_object_and_invalidate_old_caches, _do_return_non_local, _not_yet_implemented, _unknown_bytecode
from som.interpreter.bc.bytecodes import bytecode_length, Bytecodes, bytecode_as_str
from som.interpreter.bc.frame import (
    get_block_at,
    get_self_dynamically,
)
from som.interpreter.bc.method_execution_context import MethodExecutionContext
from som.interpreter.control_flow import ReturnException
from som.interpreter.send import (
    lookup_and_send_2,
    lookup_and_send_3,
    get_inline_cache_size,
    get_clean_inline_cache_and_size,
)
from som.vm.globals import nilObject, trueObject, falseObject
from som.vmobjects.array import Array
from som.vmobjects.block_bc import BcBlock
from som.vmobjects.integer import int_0, int_1

from rlib import jit
from rlib.jit import promote, elidable_promote, we_are_jitted


class Interpreter:
    jitdriver = jit.JitDriver(
        name="Interpreter",
        greens=["current_bc_idx", "stack_ptr", "method"],
        reds=["frame", "stack"],
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

    def __init__(self, method, frame, max_stack_size):
        self.method = method
        self.frame = frame
        self.max_stack_size = max_stack_size

        self.current_bc_idx = 0
        self.next_bc_idx = 0

    def _do_super_send(self, bytecode_index, method, stack, stack_ptr):
        signature = method.get_constant(bytecode_index)

        receiver_class = method.get_holder().get_super_class()
        invokable = receiver_class.lookup_invokable(signature)

        num_args = invokable.get_number_of_signature_arguments()
        receiver = stack[stack_ptr - (num_args - 1)]

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
            stack_ptr = _invoke_invokable_slow_path(
                invokable, num_args, receiver, stack, stack_ptr
            )
        else:
            stack_ptr = send_does_not_understand(
                receiver, invokable.get_signature(), stack, stack_ptr
            )
        return stack_ptr


    @jit.unroll_safe
    def interpret(self):
        from som.vm.current import current_universe

        execution_ctx = MethodExecutionContext(self.max_stack_size, no_tos_caching=True)

        while True:
            self.jitdriver.jit_merge_point(
                current_bc_idx=self.current_bc_idx,
                stack_ptr=execution_ctx.stack_ptr,
                method=self.method,
                frame=self.frame,
                stack=execution_ctx.stack,
            )

            ret_val = self.bytecode_loop(execution_ctx, current_universe)

            if ret_val is not "UNFINISHED":
                return ret_val

    def bytecode_loop(self, execution_ctx, current_universe):
        stack = execution_ctx.stack

        bytecode = self.method.get_bytecode(self.current_bc_idx)

        # Get the length of the current bytecode
        bc_length = bytecode_length(bytecode)

        # Compute the next bytecode index
        self.next_bc_idx = self.current_bc_idx + bc_length

        promote(execution_ctx.stack_ptr)

        # Handle the current bytecode
        if bytecode == Bytecodes.halt:
            return stack[execution_ctx.stack_ptr]

        if bytecode == Bytecodes.dup:
            val = stack[execution_ctx.stack_ptr]
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = val

        elif bytecode == Bytecodes.push_frame:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_frame(
                self.frame, self.method.get_bytecode(self.current_bc_idx + 1)
            )

        elif bytecode == Bytecodes.push_frame_0:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 0)

        elif bytecode == Bytecodes.push_frame_1:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 1)

        elif bytecode == Bytecodes.push_frame_2:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 2)

        elif bytecode == Bytecodes.push_inner:
            idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)

            execution_ctx.stack_ptr += 1
            if ctx_level == 0:
                stack[execution_ctx.stack_ptr] = read_inner(self.frame, idx)
            else:
                block = get_block_at(self.frame, ctx_level)
                stack[execution_ctx.stack_ptr] = block.get_from_outer(idx)

        elif bytecode == Bytecodes.push_inner_0:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 0)

        elif bytecode == Bytecodes.push_inner_1:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 1)

        elif bytecode == Bytecodes.push_inner_2:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = read_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 2)

        elif bytecode == Bytecodes.push_field:
            field_idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)
            self_obj = get_self(self.frame, ctx_level)
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self_obj.get_field(field_idx)

        elif bytecode == Bytecodes.push_field_0:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self_obj.get_field(0)

        elif bytecode == Bytecodes.push_field_1:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self_obj.get_field(1)

        elif bytecode == Bytecodes.push_block:
            block_method = self.method.get_constant(self.current_bc_idx)
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = BcBlock(block_method, get_inner_as_context(self.frame))

        elif bytecode == Bytecodes.push_block_no_ctx:
            block_method = self.method.get_constant(self.current_bc_idx)
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = BcBlock(block_method, None)

        elif bytecode == Bytecodes.push_constant:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self.method.get_constant(self.current_bc_idx)

        elif bytecode == Bytecodes.push_constant_0:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self.method._literals[0]  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_1:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self.method._literals[1]  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_constant_2:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self.method._literals[2]  # pylint: disable=protected-access

        elif bytecode == Bytecodes.push_0:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = int_0

        elif bytecode == Bytecodes.push_1:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = int_1

        elif bytecode == Bytecodes.push_nil:
            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = nilObject

        elif bytecode == Bytecodes.push_global:
            global_name = self.method.get_constant(self.current_bc_idx)
            glob = current_universe.get_global(global_name)

            execution_ctx.stack_ptr += 1
            if glob:
                stack[execution_ctx.stack_ptr] = glob
            else:
                stack[execution_ctx.stack_ptr] = lookup_and_send_2(
                    get_self_dynamically(self.frame), global_name, "unknownGlobal:"
                )

        elif bytecode == Bytecodes.pop:
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.pop_frame:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
            write_frame(self.frame, self.method.get_bytecode(self.current_bc_idx + 1), value)

        elif bytecode == Bytecodes.pop_frame_0:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
            write_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_frame_1:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
            write_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_frame_2:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
            write_frame(self.frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_inner:
            idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            if ctx_level == 0:
                write_inner(self.frame, idx, value)
            else:
                block = get_block_at(self.frame, ctx_level)
                block.set_outer(idx, value)

        elif bytecode == Bytecodes.pop_inner_0:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            write_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 0, value)

        elif bytecode == Bytecodes.pop_inner_1:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            write_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 1, value)

        elif bytecode == Bytecodes.pop_inner_2:
            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            write_inner(self.frame, FRAME_AND_INNER_RCVR_IDX + 2, value)

        elif bytecode == Bytecodes.pop_field:
            field_idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)
            self_obj = get_self(self.frame, ctx_level)

            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            self_obj.set_field(field_idx, value)

        elif bytecode == Bytecodes.pop_field_0:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)

            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            self_obj.set_field(0, value)

        elif bytecode == Bytecodes.pop_field_1:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)

            value = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

            self_obj.set_field(1, value)

        elif bytecode == Bytecodes.send_1:
            signature = self.method.get_constant(self.current_bc_idx)
            receiver = stack[execution_ctx.stack_ptr]

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, self.method, self.current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, self.method, self.current_bc_idx, current_universe
                )

            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_1(receiver)

        elif bytecode == Bytecodes.send_2:
            signature = self.method.get_constant(self.current_bc_idx)
            receiver = stack[execution_ctx.stack_ptr - 1]

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, self.method, self.current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, self.method, self.current_bc_idx, current_universe
                )

            arg = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None

            execution_ctx.stack_ptr -= 1
            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_2(receiver, arg)

        elif bytecode == Bytecodes.send_3:
            signature = self.method.get_constant(self.current_bc_idx)
            receiver = stack[execution_ctx.stack_ptr - 2]

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, self.method, self.current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, self.method, self.current_bc_idx, current_universe
                )

            arg2 = stack[execution_ctx.stack_ptr]
            arg1 = stack[execution_ctx.stack_ptr - 1]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
                stack[execution_ctx.stack_ptr - 1] = None

            execution_ctx.stack_ptr -= 2
            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_3(receiver, arg1, arg2)

        elif bytecode == Bytecodes.send_n:
            signature = self.method.get_constant(self.current_bc_idx)
            receiver = stack[
                execution_ctx.stack_ptr - (signature.get_number_of_signature_arguments() - 1)
                ]

            layout = receiver.get_object_layout(current_universe)
            dispatch_node = _lookup(
                layout, signature, self.method, self.current_bc_idx, current_universe
            )

            if isinstance(layout, GenericDispatchNode) and not layout.is_latest:
                _update_object_and_invalidate_old_caches(
                    receiver, self.method, self.current_bc_idx, current_universe
                )

            execution_ctx.stack_ptr = dispatch_node.dispatch_n_bc(execution_ctx, receiver)

        elif bytecode == Bytecodes.super_send:
            execution_ctx.stack_ptr = self._do_super_send(self.current_bc_idx, self.method, stack, execution_ctx.stack_ptr)

        elif bytecode == Bytecodes.return_local:
            return stack[execution_ctx.stack_ptr]

        elif bytecode == Bytecodes.return_non_local:
            val = stack[execution_ctx.stack_ptr]
            return _do_return_non_local(
                val, self.frame, self.method.get_bytecode(self.current_bc_idx + 1)
            )

        elif bytecode == Bytecodes.return_self:
            return read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)

        elif bytecode == Bytecodes.return_field_0:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(0)

        elif bytecode == Bytecodes.return_field_1:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(1)

        elif bytecode == Bytecodes.return_field_2:
            self_obj = read_frame(self.frame, FRAME_AND_INNER_RCVR_IDX)
            return self_obj.get_field(2)

        elif bytecode == Bytecodes.inc:
            val = stack[execution_ctx.stack_ptr]
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
            stack[execution_ctx.stack_ptr] = result

        elif bytecode == Bytecodes.dec:
            val = stack[execution_ctx.stack_ptr]
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
            stack[execution_ctx.stack_ptr] = result

        elif bytecode == Bytecodes.inc_field:
            field_idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)
            self_obj = get_self(self.frame, ctx_level)

            self_obj.inc_field(field_idx)

        elif bytecode == Bytecodes.inc_field_push:
            field_idx = self.method.get_bytecode(self.current_bc_idx + 1)
            ctx_level = self.method.get_bytecode(self.current_bc_idx + 2)
            self_obj = get_self(self.frame, ctx_level)

            execution_ctx.stack_ptr += 1
            stack[execution_ctx.stack_ptr] = self_obj.inc_field(field_idx)

        elif bytecode == Bytecodes.jump:
            self.next_bc_idx = self.current_bc_idx + self.method.get_bytecode(self.current_bc_idx + 1)

        elif bytecode == Bytecodes.jump_on_true_top_nil:
            val = stack[execution_ctx.stack_ptr]
            if val is trueObject:
                self.next_bc_idx = self.current_bc_idx + self.method.get_bytecode(self.current_bc_idx + 1)
                stack[execution_ctx.stack_ptr] = nilObject
            else:
                if we_are_jitted():
                    stack[execution_ctx.stack_ptr] = None
                execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump_on_false_top_nil:
            val = stack[execution_ctx.stack_ptr]
            if val is falseObject:
                self.next_bc_idx = self.current_bc_idx + self.method.get_bytecode(self.current_bc_idx + 1)
                stack[execution_ctx.stack_ptr] = nilObject
            else:
                if we_are_jitted():
                    stack[execution_ctx.stack_ptr] = None
                execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump_on_true_pop:
            val = stack[execution_ctx.stack_ptr]
            if val is trueObject:
                self.next_bc_idx = self.current_bc_idx + self.method.get_bytecode(self.current_bc_idx + 1)
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump_on_false_pop:
            val = stack[execution_ctx.stack_ptr]
            if val is falseObject:
                self.next_bc_idx = self.current_bc_idx + self.method.get_bytecode(self.current_bc_idx + 1)
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump_backward:
            self.next_bc_idx = self.current_bc_idx - self.method.get_bytecode(self.current_bc_idx + 1)
            self.jitdriver.can_enter_jit(
                current_bc_idx=self.next_bc_idx,
                stack_ptr=execution_ctx.stack_ptr,
                method=self.method,
                frame=self.frame,
                stack=stack,
            )

        elif bytecode == Bytecodes.jump2:
            self.next_bc_idx = (
                    self.current_bc_idx
                    + self.method.get_bytecode(self.current_bc_idx + 1)
                    + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
            )

        elif bytecode == Bytecodes.jump2_on_true_top_nil:
            val = stack[execution_ctx.stack_ptr]
            if val is trueObject:
                self.next_bc_idx = (
                        self.current_bc_idx
                        + self.method.get_bytecode(self.current_bc_idx + 1)
                        + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
                )
                stack[execution_ctx.stack_ptr] = nilObject
            else:
                if we_are_jitted():
                    stack[execution_ctx.stack_ptr] = None
                execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump2_on_false_top_nil:
            val = stack[execution_ctx.stack_ptr]
            if val is falseObject:
                self.next_bc_idx = (
                        self.current_bc_idx
                        + self.method.get_bytecode(self.current_bc_idx + 1)
                        + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
                )
                stack[execution_ctx.stack_ptr] = nilObject
            else:
                if we_are_jitted():
                    stack[execution_ctx.stack_ptr] = None
                execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump2_on_true_pop:
            val = stack[execution_ctx.stack_ptr]
            if val is trueObject:
                self.next_bc_idx = (
                        self.current_bc_idx
                        + self.method.get_bytecode(self.current_bc_idx + 1)
                        + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
                )
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump2_on_false_pop:
            val = stack[execution_ctx.stack_ptr]
            if val is falseObject:
                self.next_bc_idx = (
                        self.current_bc_idx
                        + self.method.get_bytecode(self.current_bc_idx + 1)
                        + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
                )
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1

        elif bytecode == Bytecodes.jump2_backward:
            self.next_bc_idx = self.current_bc_idx - (
                    self.method.get_bytecode(self.current_bc_idx + 1)
                    + (self.method.get_bytecode(self.current_bc_idx + 2) << 8)
            )
            self.jitdriver.can_enter_jit(
                current_bc_idx=self.next_bc_idx,
                stack_ptr=execution_ctx.stack_ptr,
                method=self.method,
                frame=self.frame,
                stack=stack,
            )

        elif bytecode == Bytecodes.q_super_send_1:
            dispatch_node = self.method.get_inline_cache(self.current_bc_idx)
            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_1(stack[execution_ctx.stack_ptr])

        elif bytecode == Bytecodes.q_super_send_2:
            dispatch_node = self.method.get_inline_cache(self.current_bc_idx)
            arg = stack[execution_ctx.stack_ptr]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
            execution_ctx.stack_ptr -= 1
            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_2(stack[execution_ctx.stack_ptr], arg)

        elif bytecode == Bytecodes.q_super_send_3:
            dispatch_node = self.method.get_inline_cache(self.current_bc_idx)
            arg2 = stack[execution_ctx.stack_ptr]
            arg1 = stack[execution_ctx.stack_ptr - 1]
            if we_are_jitted():
                stack[execution_ctx.stack_ptr] = None
                stack[execution_ctx.stack_ptr - 1] = None
            execution_ctx.stack_ptr -= 2
            stack[execution_ctx.stack_ptr] = dispatch_node.dispatch_3(stack[execution_ctx.stack_ptr], arg1, arg2)

        elif bytecode == Bytecodes.q_super_send_n:
            dispatch_node = self.method.get_inline_cache(self.current_bc_idx)
            execution_ctx.stack_ptr = dispatch_node.dispatch_n_bc(execution_ctx, None)

        elif bytecode == Bytecodes.push_local:
            self.method.patch_variable_access(self.current_bc_idx)
            # retry bytecode after patching
            self.next_bc_idx = self.current_bc_idx
        elif bytecode == Bytecodes.push_argument:
            self.method.patch_variable_access(self.current_bc_idx)
            # retry bytecode after patching
            self.next_bc_idx = self.current_bc_idx
        elif bytecode == Bytecodes.pop_local:
            self.method.patch_variable_access(self.current_bc_idx)
            # retry bytecode after patching
            self.next_bc_idx = self.current_bc_idx
        elif bytecode == Bytecodes.pop_argument:
            self.method.patch_variable_access(self.current_bc_idx)
            # retry bytecode after patching
            self.next_bc_idx = self.current_bc_idx
        else:
            _unknown_bytecode(bytecode, self.current_bc_idx, self.method)

        self.current_bc_idx = self.next_bc_idx

        return "UNFINISHED"


def send_does_not_understand(receiver, selector, stack, stack_ptr):
    # ignore self
    number_of_arguments = selector.get_number_of_signature_arguments() - 1
    arguments_array = Array.from_size(number_of_arguments)

    # Remove all arguments and put them in the freshly allocated array
    i = number_of_arguments - 1
    while i >= 0:
        value = stack[stack_ptr]
        if we_are_jitted():
            stack[stack_ptr] = None
        stack_ptr -= 1

        arguments_array.set_indexable_field(i, value)
        i -= 1

    stack[stack_ptr] = lookup_and_send_3(
        receiver, selector, arguments_array, "doesNotUnderstand:arguments:"
    )

    return stack_ptr


def jitpolicy(_driver):
    from rpython.jit.codewriter.policy import JitPolicy  # pylint: disable=import-error
    return JitPolicy()


def interpret(method, frame, max_stack_size):
    interpreter = Interpreter(method, frame, max_stack_size)
    return interpreter.interpret()
