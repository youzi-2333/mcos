"""
程序入口点。
"""

# import sys
import time
from minecraft.position import Position

# from minecraft.world import world
# from minecraft.block.range import BlockRange
# from syscore.mem.external.coding import bytes2bin
from syscore.mem.external.disk import Disk
from syscore.mem.external.dentry import Dentry


def main():
    """
    主函数。
    """
    # time.sleep(3)
    d = Disk(Position(0, 4, 0), Position(0, 4, 0).delta(16, 16, 16))
    d.format()
    print(d.bitmap)


if __name__ == "__main__":
    main()
