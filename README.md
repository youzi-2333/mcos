# MinecraftOS

这是一个在 Minecraft 中制作的简单操作系统，主要用于整活。嗯。

（这活整的可不容易啊……）

PS：别骂了别骂了，是我菜，只会写 Python……

## 运行

1. 启动 Minecraft 服务器。需安装 [RaspberryJuice](https://github.com/zhuowei/RaspberryJuice) 插件。
2. 启动 `main.py`。

```bash
python main.py
```

## 文件系统

### 基础

使用方块的组合（见 [syscore/mem/external/blocks.py](./syscore/mem/external/blocks.py)）存储数据，每个方块可以存储五位二进制。

但是我最担心的事情还是发生了。

字节（八个二进制）和方块（五个二进制）完全不兼容，他俩完全就是互素的。

这就直接导致 write 一次和分开来 write 两次不幂等。

这不仅带来了资源的浪费，还直接导致：同时读取这两段*分开来写的*数据时，会出现乱码。

怎么解决？

1. 尽量只写一次就达到最终效果。写入文件的时候，给个缓存让用户操作，关闭文件之后再给存进去。
2. 把指针精确到二进制。

思来想去还是选择方案二更好，更符合用户直观感受。

### 硬盘

每个硬盘开头有一串数据，指示其信息。其格式如下：

| 长度 | 进制 | 含义         | 示例   |
| ---- | ---- | ------------ | ------ |
| 2    | Hex  | 版本号       | 2c     |
| 4    | Hex  | 逻辑块长度   | 0400   |
| 1    | Hex  | 指针长度 n   | 6      |
| n    | Hex  | 索引节点指针 | 0001b1 |
| n    | Hex  | 索引节点长度 | 000479 |

紧随其后的是位图，指示每个逻辑块的使用情况。如果硬盘总空间为 $s$，逻辑块长度为 $b$，那么位图长度 $c$ 为：

$$
c=\lfloor \frac{s}{b} \rfloor.
$$
