### Python port of the minilzo source version 2.06 by schadocalex

# /* minilzo.c -- mini subset of the LZO real-time data compression library

#    This file is part of the LZO real-time data compression library.

#    Copyright (C) 2011 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2010 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2009 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2008 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2007 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2006 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2005 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2004 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2003 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2002 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2001 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 2000 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 1999 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 1998 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 1997 Markus Franz Xaver Johannes Oberhumer
#    Copyright (C) 1996 Markus Franz Xaver Johannes Oberhumer
#    All Rights Reserved.

#    The LZO library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as
#    published by the Free Software Foundation; either version 2 of
#    the License, or (at your option) any later version.

#    The LZO library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with the LZO library; see the file COPYING.
#    If not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

#    Markus F.X.J. Oberhumer
#    <markus@oberhumer.com>
#    http://www.oberhumer.com/opensource/lzo/
#  */

# /*
#  * NOTE:
#  *   the full LZO package can be found at
#  *   http://www.oberhumer.com/opensource/lzo/
#  */

import struct

multiply_de_bruijn_bit_position = [
    0,
    1,
    28,
    2,
    29,
    14,
    24,
    3,
    30,
    22,
    20,
    15,
    25,
    17,
    4,
    8,
    31,
    27,
    13,
    23,
    21,
    19,
    16,
    7,
    26,
    12,
    18,
    6,
    11,
    5,
    10,
    9,
]


def lzo_bitops_ctz32(v):
    return multiply_de_bruijn_bit_position[
        (((v & -v) * 0x077CB531) & 0xFFFFFFFF) >> 27
    ]  # TODO force unsigned?


def copy_nbytes(bytes_out, bytes_in, op, ip, n, step):
    assert n > 0
    while True:
        bytes_out[op : op + step] = bytes_in[ip : ip + step]
        op += step
        ip += step
        n -= step
        if n >= step:
            continue
        break

    return op, ip, n


def lzo1x_1_compress_core(bytes_in, ini_ip, in_len, bytes_out, ini_op, ti, wrkmem):
    ip = ini_ip
    op = ini_op
    in_end = ini_ip + in_len
    ip_end = ini_ip + in_len - 20
    ii = ip
    dict_ = wrkmem
    if ti < 4:
        ip += 4 - ti

    m_pos = 0
    m_off = 0
    m_len = 0

    gt_m_len_done = False
    gt_next = False

    while True:
        if gt_next:
            pass
        else:
            # literal:
            ip += 1 + ((ip - ii) >> 5)

        # next:
        gt_next = False
        if ip >= ip_end:
            break

        dv = struct.unpack_from("<I", bytes_in, ip)[0]
        dindex = (
            (((0x1824429D * dv) & 0xFFFFFFFF) >> (32 - 14)) & ((1 << 14) - 1)
        ) & 0xFFFFFFFF
        m_pos = ini_ip + dict_[dindex]  # bytes_in
        dict_[dindex] = (ip - ini_ip) & 0xFFFF
        if dv != struct.unpack_from("<I", bytes_in, m_pos)[0]:
            continue  # goto literal

        ii -= ti
        ti = 0

        tmp = (ip - ii) & 0xFFFFFFFF
        if tmp != 0:
            if tmp <= 3:
                bytes_out[op - 2] |= tmp & 0xFF
                bytes_out[op : op + 4] = bytes_in[ii : ii + 4]
                op += tmp
            elif tmp <= 16:
                bytes_out[op] = (tmp - 3) & 0xFF
                op += 1
                bytes_out[op : op + 16] = bytes_in[ii : ii + 16]
                op += tmp
            else:
                if tmp <= 18:
                    bytes_out[op] = (tmp - 3) & 0xFF
                    op += 1
                else:
                    tt = tmp - 18
                    bytes_out[op] = 0
                    op += 1
                    while tt > 255:
                        tt -= 255
                        bytes_out[op] = 0
                        op += 1

                    bytes_out[op] = tt & 0xFF
                    op += 1

                op, ii, tmp = copy_nbytes(bytes_out, bytes_in, op, ii, tmp, 16)
                if tmp > 0:
                    op, ii, tmp = copy_nbytes(bytes_out, bytes_in, op, ii, tmp, 1)

        m_len = 4
        v = (struct.unpack_from("<I", bytes_in, ip + m_len)[0]) ^ (
            struct.unpack_from("<I", bytes_in, m_pos + m_len)[0]
        )
        if v == 0:
            while True:
                m_len += 4
                v = (struct.unpack_from("<I", bytes_in, ip + m_len)[0]) ^ (
                    struct.unpack_from("<I", bytes_in, m_pos + m_len)[0]
                )
                if ip + m_len >= ip_end:
                    gt_m_len_done = True
                    break  # goto m_len_done
                if v == 0:
                    continue
                break

        if gt_m_len_done:
            pass
        else:
            m_len += lzo_bitops_ctz32(v) // 8

        # m_len_done:
        gt_m_len_done = False
        m_off = (ip - m_pos) & 0xFFFFFFFF
        ip += m_len
        ii = ip
        if m_len <= 8 and m_off <= 0x0800:
            m_off -= 1
            bytes_out[op] = (((m_len - 1) << 5) | ((m_off & 7) << 2)) & 0xFF
            op += 1
            bytes_out[op] = (m_off >> 3) & 0xFF
            op += 1
        elif m_off <= 0x4000:
            m_off -= 1
            if m_len <= 33:
                bytes_out[op] = (32 | (m_len - 2)) & 0xFF
                op += 1
            else:
                m_len -= 33
                bytes_out[op] = 32 | 0
                op += 1
                while m_len > 255:
                    m_len -= 255
                    bytes_out[op] = 0
                    op += 1
                bytes_out[op] = m_len & 0xFF
                op += 1
            bytes_out[op] = (m_off << 2) & 0xFF
            op += 1
            bytes_out[op] = (m_off >> 6) & 0xFF
            op += 1
        else:
            m_off -= 0x4000
            if m_len <= 9:
                bytes_out[op] = (16 | ((m_off >> 11) & 8) | (m_len - 2)) & 0xFF
                op += 1
            else:
                m_len -= 9
                bytes_out[op] = (16 | ((m_off >> 11) & 8)) & 0xFF
                op += 1
                while m_len > 255:
                    m_len -= 255
                    bytes_out[op] = 0
                    op += 1
                bytes_out[op] = m_len & 0xFF
                op += 1
            bytes_out[op] = (m_off << 2) & 0xFF
            op += 1
            bytes_out[op] = (m_off >> 6) & 0xFF
            op += 1

        gt_next = True
        continue

    return (in_end - (ii - ti)) & 0xFFFFFFFF, (op - ini_op) & 0xFFFFFFFF


def lzo1x_1_compress(bytes_in, bytes_out, wrkmem):
    ip = 0  # input pointer
    op = 0  # output pointer
    l = len(bytes_in)
    tmp = 0

    while l > 20:
        ll = min(l, 49152)
        ll_end = ip + ll
        if (ll_end + ((tmp + ll) >> 5)) <= ll_end:
            break

        for i in range((1 << 14) * 2):
            wrkmem[i] = 0

        tmp, out_len = lzo1x_1_compress_core(
            bytes_in, ip, ll, bytes_out, op, tmp, wrkmem
        )
        ip += ll
        op += out_len
        l -= ll

    tmp += l
    if tmp > 0:
        ii = len(bytes_in) - tmp
        if op == 0 and tmp <= 238:
            bytes_out[op] = (17 + tmp) & 0xFF
            op += 1
        elif tmp <= 3:
            bytes_out[op - 2] |= tmp & 0xFF
        elif tmp <= 18:
            bytes_out[op] = (tmp - 3) & 0xFF
            op += 1
        else:
            tt = tmp - 18
            bytes_out[op] = 0
            op += 1
            while tt > 255:
                tt -= 255
                bytes_out[op] = 0
                op += 1

            bytes_out[op] = tt & 0xFF
            op += 1

        op, ii, tmp = copy_nbytes(bytes_out, bytes_in, op, ii, tmp, 1)

    bytes_out[op] = 16 | 1
    op += 1
    bytes_out[op] = 0
    op += 1
    bytes_out[op] = 0
    op += 1

    # out_len = op
    return bytes(bytes_out[:op])


def match_next(bytes_out, bytes_in, op, ip, tmp):
    op, ip, tmp = copy_nbytes(bytes_out, bytes_in, op, ip, tmp, 1)

    tmp = bytes_in[ip]
    ip += 1

    return op, ip, tmp


def copy_match(bytes_out, op, m_pos, tmp):
    bytes_out[op] = bytes_out[m_pos]
    op += 1
    m_pos += 1
    bytes_out[op] = bytes_out[m_pos]
    op += 1
    m_pos += 1

    return copy_nbytes(bytes_out, bytes_out, op, m_pos, tmp, 1)


def lzo1x_decompress(bytes_in, bytes_out):
    ip_end = len(bytes_in)
    op = 0  # out pointer
    ip = 0  # in pointer
    tmp = 0
    m_pos = 0  # match pos
    gt_first_literal_run = False
    gt_match_done = False
    gt_match = False
    gt_eof_found = False
    gt_match_next = False

    if bytes_in[ip] > 17:
        tmp = bytes_in[ip] - 17
        ip += 1
        if tmp < 4:
            gt_match_next = True
        else:
            op, ip, tmp = copy_nbytes(bytes_out, bytes_in, op, ip, tmp, 1)

            gt_first_literal_run = True

    while True:
        if gt_first_literal_run or gt_match_next:
            pass
        else:
            tmp = bytes_in[ip]
            ip += 1

            if tmp >= 16:
                gt_match = True
            else:
                if tmp == 0:
                    while bytes_in[ip] == 0:
                        tmp += 255
                        ip += 1

                    tmp += 15 + bytes_in[ip]
                    ip += 1

                bytes_out[op : op + 4] = bytes_in[ip : ip + 4]
                op += 4
                ip += 4

                tmp -= 1
                if tmp >= 4:
                    op, ip, tmp = copy_nbytes(bytes_out, bytes_in, op, ip, tmp, 4)
                if tmp > 0:
                    op, ip, tmp = copy_nbytes(bytes_out, bytes_in, op, ip, tmp, 1)

        # first_literal_run:
        gt_first_literal_run = False
        if gt_match or gt_match_next:
            pass
        else:
            tmp = bytes_in[ip]
            ip += 1

            if tmp >= 16:
                gt_match = True
            else:
                m_pos = op - (1 + 0x0800)
                m_pos -= tmp >> 2
                m_pos -= bytes_in[ip] << 2
                ip += 1

                bytes_out[op] = bytes_out[m_pos]
                op += 1
                m_pos += 1
                bytes_out[op] = bytes_out[m_pos]
                op += 1
                m_pos += 1
                bytes_out[op] = bytes_out[m_pos]
                op += 1
                gt_match_done = True

        # match:
        gt_match = False
        while True:
            if gt_match_done or gt_match_next:
                pass
            elif tmp >= 64:
                m_pos = op - 1
                m_pos -= (tmp >> 2) & 7
                m_pos -= bytes_in[ip] << 3
                ip += 1
                tmp = (tmp >> 5) - 1

                op, m_pos, tmp = copy_match(bytes_out, op, m_pos, tmp)
                gt_match_done = True
            elif tmp >= 32:
                tmp &= 31
                if tmp == 0:
                    while bytes_in[ip] == 0:
                        tmp += 255
                        ip += 1

                    tmp += 31 + bytes_in[ip]
                    ip += 1

                m_pos = op - 1
                assert (bytes_in[ip] + (bytes_in[ip + 1] << 0x8)) == struct.unpack_from(
                    "<H", bytes_in, ip
                )[0]
                m_pos -= struct.unpack_from("<H", bytes_in, ip)[0] >> 2
                ip += 2
            elif tmp >= 16:
                m_pos = op
                m_pos -= (tmp & 8) << 11
                tmp &= 7
                if tmp == 0:
                    while bytes_in[ip] == 0:
                        tmp += 255
                        ip += 1

                    tmp += 7 + bytes_in[ip]
                    ip += 1

                assert (bytes_in[ip] + (bytes_in[ip + 1] << 0x8)) == struct.unpack_from(
                    "<H", bytes_in, ip
                )[0]
                m_pos -= struct.unpack_from("<H", bytes_in, ip)[0] >> 2
                ip += 2
                if m_pos == op:
                    gt_eof_found = True
                    break
                m_pos -= 0x4000
            else:
                m_pos = op - 1
                m_pos -= tmp >> 2
                m_pos -= bytes_in[ip] << 2
                ip += 1
                bytes_out[op] = bytes_out[m_pos]
                op += 1
                m_pos += 1
                bytes_out[op] = bytes_out[m_pos]
                op += 1
                gt_match_done = True

            if gt_match_done or gt_match_next:
                pass
            elif (tmp >= (2 * 4 - (3 - 1))) and ((op - m_pos) >= 4):
                bytes_out[op : op + 4] = bytes_out[m_pos : m_pos + 4]
                op += 4
                m_pos += 4
                tmp -= 4 - (3 - 1)

                op, m_pos, tmp = copy_nbytes(bytes_out, bytes_out, op, m_pos, tmp, 4)
                if tmp > 0:
                    op, m_pos, tmp = copy_nbytes(
                        bytes_out, bytes_out, op, m_pos, tmp, 1
                    )
            else:
                # copy_match:
                op, m_pos, tmp = copy_match(bytes_out, op, m_pos, tmp)

            # match_done:
            if gt_match_next:
                pass
            else:
                gt_match_done = False
                tmp = bytes_in[ip - 2] & 3
                if tmp == 0:
                    break

            # match_next:
            gt_match_next = False
            bytes_out[op] = bytes_in[ip]
            op += 1
            ip += 1

            if tmp > 1:
                bytes_out[op] = bytes_in[ip]
                op += 1
                ip += 1
                if tmp > 2:
                    bytes_out[op] = bytes_in[ip]
                    op += 1
                    ip += 1

            tmp = bytes_in[ip]
            ip += 1

        if gt_eof_found:
            break

    # eof_found:
    # out_len = op
    assert len(bytes_out) == op
    if ip == ip_end:
        return 0
    elif ip < ip_end:
        return -8
    else:
        return -4


def decompress(bytes_in, out_len):
    assert isinstance(out_len, int)
    bytes_out = bytearray(out_len)
    lzo1x_decompress(bytes_in, bytes_out)
    return bytes(bytes_out)


def compress(bytes_in):
    bytes_out = bytearray(len(bytes_in) + (len(bytes_in) // 16) + 64 + 3)
    wrkmem = [0] * ((1 << 14) * 2)
    return lzo1x_1_compress(bytes_in, bytes_out, wrkmem)


# public static unsafe byte[] Decompress(byte[] @in, byte[] @out)
# {
#     uint out_len = 0;
#     fixed (byte* @pIn = @in, wrkmem = new byte[IntPtr.Size * 16384], pOut = @out)
#     {
#         lzo1x_decompress(pIn, (uint)@in.Length, @pOut, ref @out_len, wrkmem);
#     }
#     return @out;
# }

# public static unsafe void Decompress(byte* r, uint size_in, byte* w, ref uint size_out)
# {
#     fixed (byte* wrkmem = new byte[IntPtr.Size * 16384])
#     {
#         lzo1x_decompress(r, size_in, w, ref size_out, wrkmem);
#     }
# }

# public static unsafe byte[] Compress(byte[] input)
# {
#     byte[] @out = new byte[input.Length + (input.Length / 16) + 64 + 3];
#     uint out_len = 0;
#     fixed (byte* @pIn = input, wrkmem = new byte[IntPtr.Size * 16384], pOut = @out)
#     {
#         lzo1x_1_compress(pIn, (uint)input.Length, @pOut, ref @out_len, wrkmem);
#     }
#     Array.Resize(ref @out, (int)out_len);
#     return @out;
# }

# public static unsafe void Compress(byte* r, uint size_in, byte* w, ref uint size_out)
# {
#     fixed (byte* wrkmem = new byte[IntPtr.Size * 16384])
#     {
#         lzo1x_1_compress(r, size_in, w, ref size_out, wrkmem);
#     }
# }
