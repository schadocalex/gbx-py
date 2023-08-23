import itertools

from construct import Subconstruct, ListContainer, evaluate


class MyRepeatUntil(Subconstruct):
    r"""
    Same as construct but can access to previous intermediate values


    Homogenous array of elements, similar to C# generic IEnumerable<T>, that repeats until the predicate indicates it to stop. Note that the last element (that predicate indicated as True) is included in the return list.

    Parse iterates indefinately until last element passed the predicate. Build iterates indefinately over given list, until an element passed the precicate (or raises RepeatError if no element passed it). Size is undefined.

    :param predicate: lambda that takes (obj, list, context) and returns True to break or False to continue (or a truthy value)
    :param subcon: Construct instance, subcon used to parse and build each element
    :param discard: optional, bool, if set then parsing returns empty list

    :raises StreamError: requested reading negative amount, could not read enough bytes, requested writing different amount than actual data, or could not write all bytes
    :raises RepeatError: consumed all elements in the stream but neither passed the predicate

    Can propagate any exception from the lambda, possibly non-ConstructError.

    Example::

        >>> d = RepeatUntil(lambda x,lst,ctx: x > 7, Byte)
        >>> d.build(range(20))
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08'
        >>> d.parse(b"\x01\xff\x02")
        [1, 255]

        >>> d = RepeatUntil(lambda x,lst,ctx: lst[-2:] == [0,0], Byte)
        >>> d.parse(b"\x01\x00\x00\xff")
        [1, 0, 0]
    """

    def __init__(self, predicate, subcon, discard=False):
        super().__init__(subcon)
        self.predicate = predicate
        self.discard = discard

    def _parse(self, stream, context, path):
        predicate = self.predicate
        discard = self.discard
        if not callable(predicate):
            predicate = lambda _1, _2, _3: predicate
        obj = ListContainer()
        context._array = obj
        for i in itertools.count():
            context._index = i
            e = self.subcon._parsereport(stream, context, path)
            if not discard:
                obj.append(e)
            if predicate(e, obj, context):
                return obj

    def _build(self, obj, stream, context, path):
        predicate = self.predicate
        discard = self.discard
        if not callable(predicate):
            predicate = lambda _1, _2, _3: predicate
        partiallist = ListContainer()
        retlist = ListContainer()
        context._array = retlist
        for i, e in enumerate(obj):
            context._index = i
            buildret = self.subcon._build(e, stream, context, path)
            if not discard:
                retlist.append(buildret)
                partiallist.append(buildret)
            if predicate(e, partiallist, context):
                break
        else:
            raise RepeatError(
                "expected any item to match predicate, when building", path=path
            )
        return retlist

    def _sizeof(self, context, path):
        raise SizeofError(
            "cannot calculate size, amount depends on actual data", path=path
        )

    def _emitparse(self, code):
        fname = f"parse_repeatuntil_{code.allocateId()}"
        block = f"""
            def {fname}(io, this):
                list_ = ListContainer()
                while True:
                    obj_ = {self.subcon._compileparse(code)}
                    if not ({self.discard}):
                        list_.append(obj_)
                    if ({self.predicate}):
                        return list_
        """
        code.append(block)
        return f"{fname}(io, this)"

    def _emitbuild(self, code):
        fname = f"build_repeatuntil_{code.allocateId()}"
        block = f"""
            def {fname}(obj, io, this):
                objiter = iter(obj)
                list_ = ListContainer()
                while True:
                    obj_ = reuse(next(objiter), lambda obj: {self.subcon._compilebuild(code)})
                    list_.append(obj_)
                    if ({self.predicate}):
                        return list_
        """
        code.append(block)
        return f"{fname}(obj, io, this)"

    def _emitfulltype(self, ksy, bitwise):
        return dict(
            type=self.subcon._compileprimitivetype(ksy, bitwise),
            repeat="until",
            repeat_until=repr(self.predicate).replace("obj_", "_"),
        )
