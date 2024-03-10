import itertools

from construct import (
    Subconstruct,
    ListContainer,
    evaluate,
    Construct,
    Struct,
    StreamError,
    RepeatError,
    ExplicitError,
    SelectError,
    stream_tell,
    stream_seek,
    stream_write,
)


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
        obj = []
        context._array = obj
        context._chunks = {}
        for i in itertools.count():
            context._index = i
            e = self.subcon._parsereport(stream, context, path)
            if not discard:
                obj.append(e)
                if "chunkId" in e and "chunk" in e:
                    context._chunks[e.chunkId] = e.chunk
            if predicate(e, obj, context):
                return obj

    def _build(self, obj, stream, context, path):
        predicate = self.predicate
        discard = self.discard
        if not callable(predicate):
            predicate = lambda _1, _2, _3: predicate
        partiallist = []
        retlist = ListContainer()
        context._array = retlist
        context._chunks = {}
        for i, e in enumerate(obj):
            context._index = i
            if "chunkId" in e and "chunk" in e:
                context._chunks[e.chunkId] = e.chunk
            buildret = self.subcon._build(e, stream, context, path)
            if not discard:
                retlist.append(buildret)
                partiallist.append(buildret)
            if predicate(e, partiallist, context):
                break
        else:
            raise RepeatError("expected any item to match predicate, when building", path=path)
        return retlist

    def _sizeof(self, context, path):
        raise SizeofError("cannot calculate size, amount depends on actual data", path=path)

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


def save_context(ctx):
    nodes = ctx._root._params.nodes
    return {
        "nodes": list(nodes) if nodes is not None else None,
        "lookbackstring_table": dict(ctx._root._params.gbx_data.get("lookbackstring_table", {})),
        "lookbackstring_index": ctx._root._params.gbx_data.get("lookbackstring_index", 0),
        "lookbackstring_version": ctx._root._params.gbx_data.get("lookbackstring_version", False),
    }


def load_context(ctx, old_ctx):
    ctx._root._params.nodes = list(old_ctx["nodes"]) if old_ctx["nodes"] is not None else None
    ctx._root._params.gbx_data["lookbackstring_table"] = dict(old_ctx["lookbackstring_table"])
    ctx._root._params.gbx_data["lookbackstring_index"] = old_ctx["lookbackstring_index"]
    ctx._root._params.gbx_data["lookbackstring_version"] = old_ctx["lookbackstring_version"]


class DebugStruct(Struct):
    r"""
    Debug a Struct with the "no subconstruct match" error
    """

    def _parse(self, stream, context, path):
        old_ctx = save_context(context)
        fallback = stream_tell(stream, path)

        try:
            return super()._parse(stream, context, path)
        except ExplicitError:
            raise
        except Exception as e:
            print(e)

            # there's an error, try to reduce the struct until no more error
            subcons = list(self.subcons)
            obj = None
            while subcons:
                # remove last subcon
                subcon_in_error = subcons.pop()
                if not subcons:
                    raise ExplicitError("No substructure match found")

                # Reload context
                load_context(context, old_ctx)
                stream_seek(stream, fallback, 0, path)

                try:
                    obj = Struct(*subcons)._parse(stream, context, path)
                    print(f"Debug successful, subcon in error is: {subcon_in_error}")
                    return obj
                except ExplicitError:
                    raise
                except Exception:
                    continue

        return obj

    def _build(self, obj, stream, context, path):
        old_ctx = save_context(context)

        try:
            return super()._build(obj, stream, context, path)
        except ExplicitError:
            raise
        except Exception as e:
            print(e)
            # there's an error, try to reduce the struct until no more error
            subcons = list(self.subcons)
            while subcons:
                # remove last subcon
                subcon_in_error = subcons.pop()
                if not subcons:
                    raise ExplicitError("No substructure match found")

                # Reload context
                load_context(context, old_ctx)

                try:
                    Struct(*subcons)._build(obj, stream, context, path)
                    raise ExplicitError(f"Debug successful, subcon in error is: {subcon_in_error}")
                except ExplicitError:
                    raise
                except Exception:
                    continue


class MySelect(Construct):
    r"""
    Same as Select but keep the same context for each iteration

    Selects the first matching subconstruct.

    Parses and builds by literally trying each subcon in sequence until one of them parses or builds without exception. Stream gets reverted back to original position after each failed attempt, but not if parsing succeeds. Size is not defined.

    :param \*subcons: Construct instances, list of members, some can be anonymous
    :param \*\*subconskw: Construct instances, list of members (requires Python 3.6)

    :raises StreamError: requested reading negative amount, could not read enough bytes, requested writing different amount than actual data, or could not write all bytes
    :raises StreamError: stream is not seekable and tellable
    :raises SelectError: neither subcon succeded when parsing or building

    Example::

        >>> d = Select(Int32ub, CString("utf8"))
        >>> d.build(1)
        b'\x00\x00\x00\x01'
        >>> d.build(u"Афон")
        b'\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd\x00'

        Alternative syntax, but requires Python 3.6 or any PyPy:
        >>> Select(num=Int32ub, text=CString("utf8"))
    """

    def __init__(self, *subcons, **subconskw):
        super().__init__()
        self.subcons = list(subcons) + list(k / v for k, v in subconskw.items())
        self.flagbuildnone = any(sc.flagbuildnone for sc in self.subcons)

    def _parse(self, stream, context, path):
        old_ctx = save_context(context)
        for i, sc in enumerate(self.subcons):
            if i > 0:
                load_context(context, old_ctx)

            fallback = stream_tell(stream, path)
            try:
                obj = sc._parsereport(stream, context, path)
            except ExplicitError:
                raise
            except Exception:
                stream_seek(stream, fallback, 0, path)
            else:
                return obj
        raise SelectError("no subconstruct matched", path=path)

    def _build(self, obj, stream, context, path):
        old_ctx = save_context(context)
        for i, sc in enumerate(self.subcons):
            if i > 0:
                load_context(context, old_ctx)

            try:
                data = sc.build(obj, **context)
            except ExplicitError:
                raise
            except Exception:
                pass
            else:
                stream_write(stream, data, len(data), path)
                return obj
        raise SelectError("no subconstruct matched: %s" % (obj,), path=path)
