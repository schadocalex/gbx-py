import math

from construct import Container


def quaternion_from_matrix(M):
    """Return quaternion from rotation matrix.
    from https://github.com/ros/geometry/blob/fe344b6c848b8239750ad7f8c7eccf86241396d3/tf/src/tf/transformations.py#L1196
    """

    # assume M[3,3] is 1

    q = Container(x=0, y=0, z=0, w=1)
    t = M.XX + M.YY + M.ZZ + 1
    if t > 1:
        q.w = t
        q.z = M.YX - M.XY
        q.y = M.XZ - M.ZX
        q.x = M.ZY - M.YZ
    else:
        i, j, k = "X", "Y", "Z"
        if M.YY > M.XX:
            i, j, k = "Y", "Z", "X"
        if M.ZZ > M[i + i]:
            i, j, k = "Z", "X", "Y"
        t = M[i + i] - (M[j + j] + M[k + k]) + 1
        q[i.lower()] = t
        q[j.lower()] = M[i + j] + M[j + i]
        q[k.lower()] = M[k + i] + M[i + k]
        q.w = M[k + j] - M[j + k]

    coeff = 0.5 / math.sqrt(t * 1)
    q.x *= coeff
    q.y *= coeff
    q.z *= coeff
    q.w *= coeff

    return q


# axis sequences for Euler angles
_NEXT_AXIS = [1, 2, 0, 1]

# map axes strings to/from tuples of inner axis, parity, repetition, frame
_AXES2TUPLE = {
    "sxyz": (0, 0, 0, 0),
    "sxyx": (0, 0, 1, 0),
    "sxzy": (0, 1, 0, 0),
    "sxzx": (0, 1, 1, 0),
    "syzx": (1, 0, 0, 0),
    "syzy": (1, 0, 1, 0),
    "syxz": (1, 1, 0, 0),
    "syxy": (1, 1, 1, 0),
    "szxy": (2, 0, 0, 0),
    "szxz": (2, 0, 1, 0),
    "szyx": (2, 1, 0, 0),
    "szyz": (2, 1, 1, 0),
    "rzyx": (0, 0, 0, 1),
    "rxyx": (0, 0, 1, 1),
    "ryzx": (0, 1, 0, 1),
    "rxzx": (0, 1, 1, 1),
    "rxzy": (1, 0, 0, 1),
    "ryzy": (1, 0, 1, 1),
    "rzxy": (1, 1, 0, 1),
    "ryxy": (1, 1, 1, 1),
    "ryxz": (2, 0, 0, 1),
    "rzxz": (2, 0, 1, 1),
    "rxyz": (2, 1, 0, 1),
    "rzyz": (2, 1, 1, 1),
}

_TUPLE2AXES = dict((v, k) for k, v in _AXES2TUPLE.items())


def quaternion_from_euler(ai, aj, ak, axes="szxy"):
    """Return quaternion from Euler angles and axis sequence.
    from https://github.com/ros/geometry/blob/fe344b6c848b8239750ad7f8c7eccf86241396d3/tf/src/tf/transformations.py#L1100
    ai, aj, ak : Euler's roll, pitch and yaw angles
    axes : One of 24 axis sequences as string or encoded tuple

    szxy by default for TM
    """
    try:
        firstaxis, parity, repetition, frame = _AXES2TUPLE[axes.lower()]
    except (AttributeError, KeyError):
        _ = _TUPLE2AXES[axes]
        firstaxis, parity, repetition, frame = axes

    i = firstaxis
    j = _NEXT_AXIS[i + parity]
    k = _NEXT_AXIS[i - parity + 1]

    if frame:
        ai, ak = ak, ai
    if parity:
        aj = -aj

    ai = ai / 2.0
    aj = aj / 2.0
    ak = ak / 2.0
    ci = math.cos(ai)
    si = math.sin(ai)
    cj = math.cos(aj)
    sj = math.sin(aj)
    ck = math.cos(ak)
    sk = math.sin(ak)
    cc = ci * ck
    cs = ci * sk
    sc = si * ck
    ss = si * sk

    quaternion = [0, 0, 0, 0]
    if repetition:
        quaternion[i] = cj * (cs + sc)
        quaternion[j] = sj * (cc + ss)
        quaternion[k] = sj * (cs - sc)
        quaternion[3] = cj * (cc - ss)
    else:
        quaternion[i] = cj * sc - sj * cs
        quaternion[j] = cj * ss + sj * cc
        quaternion[k] = cj * cs - sj * sc
        quaternion[3] = cj * cc + sj * ss
    if parity:
        quaternion[j] *= -1

    return Container(x=quaternion[0], y=quaternion[1], z=quaternion[2], w=quaternion[3])
