"""
硬盘。
"""

import math
from typing import Optional
from minecraft.block.range import BlockRange
from minecraft.position import Position
from minecraft.world import world
from syscore.mem.external.blocks import digits2block, get_block, get_data
from syscore.mem.external.coding import bin2digits, bin2bytes, bytes2bin
from syscore.base import int2bin
from syscore.mem.external.logical import Logical, LogicalResult

VERSION_CODE = 0
"""
版本号。
"""
BITMAP_START = 7
"""
位图起始点指针，单位为半字节（位十六进制）。
"""


def loc2pos(p1: Position, dx: float, dy: float, loc: int) -> Position:
    """
    获取指定位置的坐标。
    """
    block = loc // 5
    return p1.delta(
        (block // dy) % dx,
        block % dy,
        block // (dx * dy),
    )


class Disk(BlockRange):
    """
    硬盘。

    读写顺序：Y-X-Z，以避免多次 tp 玩家加载区块。

    `p1` `p2` 属性指示其实际可用的空间（而非外壳顶点坐标）。
    """

    _loc: int = 0

    @property
    def loc(self) -> int:
        """磁头指针位置（位）。"""
        return self._loc

    @loc.setter
    def loc(self, new: int):
        """设置磁头指针位置。"""
        if not 0 <= new < self.size:
            raise ValueError(f"{new} is out of range [0,{self.size})")
        self._loc = new

    @property
    def loc_pos(self) -> Position:
        """磁头指针指向的方块。"""
        return loc2pos(self.p1, self.delta_x, self.delta_y, self.loc)

    @property
    def loc_bin(self):
        """磁头指针指向方块的二进制数据。总是五位。"""
        return bin(get_data(world.get(self.loc_pos))).replace("0b", "").zfill(5)

    @loc_bin.setter
    def loc_bin(self, other: str):
        world.set(self.loc_pos, get_block(int(other, 2)))

    @property
    def loc_int(self):
        """磁头指针指向方块的整数数据。总是五位二进制。"""
        return get_data(world.get(self.loc_pos))

    @property
    def bit(self) -> int:
        """大小，单位为字节（8 位）。"""
        return math.floor(self.size * 0.125)

    @property
    def size(self) -> int:
        """大小，单位为位。"""
        return round(self.delta_x) * round(self.delta_y) * round(self.delta_z) * 5

    version: int
    """版本号。"""
    ptr_len: int
    """指针长度（位）。"""
    logical_len: int
    """逻辑块长度（位）。"""

    @property
    def actual_logical(self) -> int:
        """实际逻辑块长度（位）。"""
        return self.logical_len - self.ptr_len - 1

    def generate_shell(self):
        """
        生成外壳。
        """
        world.fill(
            BlockRange(self.p1.delta(-2, -2, -2), self.p2.delta(2, 2, 2)),
            block=251,  # 混凝土
            data=8,
            hollow=True,
        )
        world.fill(
            BlockRange(self.p1.delta(-1, -1, -1), self.p2.delta(1, 1, 1)),
            block=49,  # 黑曜石
            hollow=True,
        )

    def _load_super(self):
        """
        加载超级块。
        """
        self.loc = 0
        self.version = self._read_num(8)
        self.logical_len = self._read_num(16)
        self.ptr_len = self._read_num(4)

    @property
    def bitmap(self):
        """
        位图。
        """
        backup_loc = self.loc

        self.loc = 7 * 4
        result = self._read_bin(self.logical_count)

        self.loc = backup_loc
        return list(result)

    @bitmap.setter
    def bitmap(self, other: list):
        backup_loc = self.loc

        self.loc = 7 * 4
        self._write_bin("".join(other))

        self.loc = backup_loc

    def _set_bitmap(self, key: int, val: bool):
        backup_loc = self.loc

        self.loc = 7 * 4 + key
        self._write_bin("1" if val else "0")

        self.loc = backup_loc

    @property
    def logical_count(self):
        """逻辑块数量。"""
        return math.floor(self.size / self.logical_len)

    def _read_bin(self, length_bin: int) -> str:
        """
        读取二进制数据。
        """
        padding = self.loc % 5
        start_pos = self.loc
        binary = ""
        for _ in range(length_bin // 5 + 2):
            binary += self.loc_bin
            self.loc += 5

        self.loc = start_pos + length_bin
        return binary[padding : padding + length_bin]

    def _read_num(self, length_bin: int) -> int:
        """
        读取数字。
        """
        padding = self.loc % 5
        start_pos = self.loc
        binary = ""
        for _ in range(length_bin // 5 + 2):
            binary += self.loc_bin
            self.loc += 5

        self.loc = start_pos + length_bin
        return int(binary[padding : padding + length_bin], 2)

    def read(self, length_bin: int) -> bytes:
        """
        读取。
        """
        # 说白了，就是从一堆方块里面整出二进制数据，然后拿出我想要的
        padding = self.loc % 5
        start_pos = self.loc
        binary = ""
        for _ in range(length_bin // 5 + 2):
            binary += self.loc_bin
            self.loc += 5

        self.loc = start_pos + length_bin
        return bin2bytes(binary[padding : padding + length_bin])

    def _write_bin(self, data: str):
        """
        写入二进制数据。
        """
        if data.startswith("0b"):
            data = data[2:]
        padding = self.loc % 5
        binary = self.loc_bin[:padding]
        if padding != 0:
            self.loc -= padding
        binary += data
        blocks = digits2block(bin2digits(binary))
        for block in blocks:
            world.set(self.loc_pos, block)
            self.loc += 5
        self.loc -= 5 - len(binary) % 5

    def _write_num(self, data: int, length_bin: int):
        """
        写入数字。
        """
        # 其实就是把二进制数据补全，然后写进方块
        padding = self.loc % 5
        binary = self.loc_bin[:padding]

        if padding != 0:
            self.loc -= padding
        binary += int2bin(data, length_bin)

        blocks = digits2block(bin2digits(binary))
        for block in blocks:
            world.set(self.loc_pos, block)
            self.loc += 5
        self.loc -= 5 - len(binary) % 5

    def write(self, data: bytes):
        """
        写入。
        """
        # 其实就是把二进制数据补全，然后写进方块
        padding = self.loc % 5
        binary = self.loc_bin[:padding]

        if padding != 0:
            self.loc -= padding
        binary += bytes2bin(data)

        blocks = digits2block(bin2digits(binary))
        for block in blocks:
            world.set(self.loc_pos, block)
            self.loc += 5
        self.loc -= 5 - len(binary) % 5

    def get_valid_logical(self):
        """
        获取可用的逻辑块序号。
        """
        return self.bitmap.index("0")

    def logical_read(self, logical: int):
        """
        读取逻辑块。
        """
        result = bytearray()
        is_dentry = None
        next_logical = logical
        while True:
            result += (read_logical := self._logical_direct_read(next_logical)).data
            next_logical = read_logical.next_logical
            if is_dentry is None:
                is_dentry = read_logical.is_dentry
            if next_logical == 0:
                break
        return LogicalResult(is_dentry, bytes(result))

    def _logical_direct_read(self, logical: int):
        self.loc = logical * self.logical_len
        is_dentry = self._read_bin(1) == "1"  # 是否为目录项
        data = self.read(self.actual_logical)
        next_logical = round(self._read_num(self.ptr_len) / self.logical_len)
        return Logical(is_dentry, data, next_logical)

    def logical_write(
        self, logical: int, data: bytes, is_dentry: Optional[bool] = None
    ):
        """
        写入逻辑块。
        """
        self.loc = logical * self.logical_len
        new_logical = logical
        bin_data = bytes2bin(data)
        for i in range(len(bin_data) // self.actual_logical + 1):
            new_logical = self._logical_direct_write(
                new_logical,
                bin_data[
                    i
                    * self.actual_logical : min(
                        (i + 1) * self.actual_logical, len(bin_data)
                    )
                ],
                is_dentry,
            )

    def _logical_direct_write(
        self,
        logical: int,
        data: str,
        is_dentry: Optional[bool] = None,
        next_logical: int = -1,
        is_end: bool = False,
    ):
        """
        直接写入逻辑块。

        若指定 `next_logical`，则写入特定的下一个逻辑块指针，否则自动读取，并返回逻辑块序号。
        """
        if (l := len(data)) > self.actual_logical:
            raise ValueError(
                f"数据长度 {l} 位超过逻辑块实际数据大小 {self.actual_logical} 位。"
            )
        self.loc = logical * self.logical_len
        if is_dentry is not None:
            self._write_bin("1" if is_dentry else "0")  # 指明是否为目录项
        else:
            self.loc += 1  # 不操作
        self._write_bin(data)
        self._set_bitmap(logical, True)
        self.loc = (logical + 1) * self.logical_len - self.ptr_len
        if next_logical == -1:
            # 自动读取下一个逻辑块
            # 如果读到了，那么直接返回
            # 如果没读到，那么获取到可用的逻辑块，写入，返回（唯一例外是如果 is_end 为真，则不读取并返回 -1）
            read_next_logical = self._read_num(self.ptr_len)
            if read_next_logical == 0:  # 没读到
                if is_end:
                    return -1
                next_logical = self.get_valid_logical()
                self.loc -= self.ptr_len
                self._write_num(next_logical * self.logical_len, self.ptr_len)
                return next_logical
            # 读到了
            return read_next_logical // self.logical_len
        self._write_num(next_logical * self.logical_len, self.ptr_len)
        return next_logical

    def logical_clear(self, logical: int):
        """
        清空逻辑块。返回下一个逻辑块序号。
        """
        self.loc = logical * self.logical_len
        self._write_bin("0" * (self.actual_logical + 1))
        next_logical = self._read_num(self.ptr_len)  # 读取下一个逻辑块序号
        self.loc -= self.ptr_len
        self._write_num(0, self.ptr_len)  # 清空下一个逻辑块序号
        self._set_bitmap(logical, False)
        return next_logical

    def _clear(self):
        """
        清空。
        """
        try:
            self.loc = 0
            while True:
                self.write(b"\x00\x00\x00\x00\x00")
        except ValueError:  # 写入完成
            self.loc = 0
            return True
        except:  # pylint: disable=W0702
            self.loc = 0
            return False

    def format(self, logical: int = 1024):
        """
        格式化。

        ### 参数
        - `logical`：每个逻辑块的大小，单位为字节。
        """
        if not 0x200 <= logical <= 0xFFFF:
            raise ValueError(f"逻辑块大小不合法：应为 [512, 65535]，实为 {logical}。")
        self._clear()
        self.loc = 0
        self.logical_len = logical * 8

        self._write_num(VERSION_CODE, 2 * 4)  # 版本号
        self._write_num(logical, 4 * 4)  # 逻辑块长度
        self.ptr_len = len(bin(self.size)) - 2
        self._write_num(self.ptr_len, 1 * 4)  # 指针长度

        self.bitmap = ["0" for _ in range(self.logical_count)]  # 位图
        len_bitmap = len(self.bitmap)
        for i in range((len_bitmap + 7 * 4) // self.logical_len + 1):
            self._set_bitmap(i, True)
        self._load_super()
