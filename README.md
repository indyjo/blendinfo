# blendinfo
Utility to analyze the contents of a .blend file (Blender's internal file format).

```
usage: blendinfo.py [-h] [--info] [--dna] [--id] PATH

Examines .blend files and prints information

positional arguments:
  PATH        .blend file to examine

optional arguments:
  -h, --help  show this help message and exit
  --info      Print information about the .blend file itself
  --dna       Print detailed information about DNA structs
  --id        Print summary on 'ID' structs
```
The output is empty unless one of the information-selecting arguments is given (--info, --dna etc.).

Example:
```
> blendinfo.py --info barbershop_interior_cpu.blend
Blend file: Little-endian, 64 bit pointers

> blendinfo.py --id barbershop_interior_cpu.blend
5722 of 254794 datablocks containing 5722 of 10492836 objects totalling 7432040 of 281459712 bytes are ID

> blendinfo.py --dna barbershop_interior_cpu.blend | head -n 30
struct Link // 16 bytes [#0]
    Link       *next                 //    8 bytes, offset 0
    Link       *prev                 //    8 bytes, offset 8
struct LinkData // 24 bytes [#1]
    LinkData   *next                 //    8 bytes, offset 0
    LinkData   *prev                 //    8 bytes, offset 8
    void       *data                 //    8 bytes, offset 16
struct ListBase // 16 bytes [#2]
    void       *first                //    8 bytes, offset 0
    void       *last                 //    8 bytes, offset 8
struct vec2s // 4 bytes [#3]
    short      x                     //    2 bytes, offset 0
    short      y                     //    2 bytes, offset 2
struct vec2f // 8 bytes [#4]
    float      x                     //    4 bytes, offset 0
    float      y                     //    4 bytes, offset 4
[ ... and thousands more ...]
```
