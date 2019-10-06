# blendinfo
Utility to analyze the contents of a .blend file (Blender's internal file format).

```
usage: blendinfo.py [-h] [--info] [--dna] [--dump] [--id] [--dot] [--size]
                    [--find ADDR]
                    PATH

Examines .blend files and prints information

positional arguments:
  PATH         .blend file to examine

optional arguments:
  -h, --help   show this help message and exit
  --info       Print information about the .blend file itself
  --dna        Print detailed information about DNA structs
  --dump       Print contents of all contained DNA data
  --id         Print summary on 'ID' structs
  --dot        Print dot graph fo whole file
  --size       Print statistic on size claimed by data types
  --find ADDR  Finds the given address in the file's data
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

> blendinfo.py --find 7f19958b56ff barbershop_interior_cpu.blend
Found address 7f19958b56ff in OB segment of size 1440 at 7f19958b5608 containing 1 Object of size 1440
{ // 1440 bytes
  ID id = { // 120 bytes
    void *next = 7f19958b5c08
    void *prev = 7f19958b5008
    ID *newid = 0
    Library *lib = 0
    char name[66] // 66 bytes
    short flag = 0
    short tag = 132
    short pad_s1 = 0
    int us = 1
    int icon_id = 0
    IDProperty *properties = 7f1995878108
  }
  AnimData *adt = 0
  SculptSession *sculpt = 0
  short type = 2
  short partype = 0
  int par1 = 0
  int par2 = 0
  int par3 = 0
  char parsubstr[64] // 64 bytes
  Object *parent = 0
  Object *track = 0
  Object *proxy = 0
  Object *proxy_group = 0
  Object *proxy_from = 0
  [ ...  many more fields ... ]
}
```
