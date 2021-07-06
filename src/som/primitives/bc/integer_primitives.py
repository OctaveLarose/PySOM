from rlib import jit
from som.interpreter.bc.frame import stack_push, stack_pop

from som.primitives.integer_primitives import IntegerPrimitivesBase as _Base
from som.vmobjects.double import Double
from som.vmobjects.integer import Integer
from som.vmobjects.primitive import Primitive, TernaryPrimitive

from som.vmobjects.block_bc import BcBlock


def get_printable_location(block_method):
    from som.vmobjects.method_bc import BcAbstractMethod

    assert isinstance(block_method, BcAbstractMethod)
    return "to:do: [%s>>%s]" % (
        block_method.get_holder().get_name().get_embedded_string(),
        block_method.get_signature().get_embedded_string(),
    )


jitdriver_int = jit.JitDriver(
    name="to:do: with int",
    greens=["block_method"],
    reds="auto",
    # virtualizables=['frame'],
    is_recursive=True,
    get_printable_location=get_printable_location,
)

jitdriver_double = jit.JitDriver(
    name="to:do: with double",
    greens=["block_method"],
    reds="auto",
    # virtualizables=['frame'],
    is_recursive=True,
    get_printable_location=get_printable_location,
)


def _to_do_int(i, by_increment, top, context, block_method):
    assert isinstance(i, int)
    assert isinstance(top, int)
    while i <= top:
        jitdriver_int.jit_merge_point(block_method=block_method)

        b = BcBlock(block_method, context)
        block_method.invoke_2(b, Integer(i))
        i += by_increment


def _to_do_double(i, by_increment, top, context, block_method):
    assert isinstance(i, int)
    assert isinstance(top, float)
    while i <= top:
        jitdriver_double.jit_merge_point(block_method=block_method)

        b = BcBlock(block_method, context)
        block_method.invoke_2(b, Integer(i))
        i += by_increment


def _to_do(rcvr, limit, block):
    block_method = block.get_method()
    context = block.get_context()

    i = rcvr.get_embedded_integer()
    if isinstance(limit, Double):
        _to_do_double(i, 1, limit.get_embedded_double(), context, block_method)
    else:
        _to_do_int(i, 1, limit.get_embedded_integer(), context, block_method)

    return rcvr


def _to_by_do(_ivkbl, frame):
    block = stack_pop(frame)
    by_increment = stack_pop(frame)
    limit = stack_pop(frame)
    self = stack_pop(frame)  # we do leave it on there

    block_method = block.get_method()
    context = block.get_context()

    i = self.get_embedded_integer()
    if isinstance(limit, Double):
        _to_do_double(
            i,
            by_increment.get_embedded_integer(),
            limit.get_embedded_double(),
            context,
            block_method,
        )
    else:
        _to_do_int(
            i,
            by_increment.get_embedded_integer(),
            limit.get_embedded_integer(),
            context,
            block_method,
        )

    stack_push(frame, self)


class IntegerPrimitives(_Base):
    def install_primitives(self):
        _Base.install_primitives(self)
        self._install_instance_primitive(
            TernaryPrimitive("to:do:", self.universe, _to_do)
        )
        self._install_instance_primitive(
            Primitive("to:by:do:", self.universe, _to_by_do)
        )
