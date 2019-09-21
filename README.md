# blendinfo
Very small utility to analyze the contents of a .blend file (Blender's internal file format).

Usage: python3 blendinfo.py somefile.blend

The output is a rough dump of the contents of the file which can be further examined using text-based tools.

Example:
```
Header: b'BLENDER-v279'
 -> pointer size: 8
 -> big endian:   False
Block: b'REND'
 -> size (bytes): 72
 -> SDNA index:   0
 ->      count:   1
 -> old pointer:  140732920679952
Block: b'TEST'
 -> size (bytes): 65544
 -> SDNA index:   0
 ->      count:   1
 -> old pointer:  4736246280
Block: b'GLOB'
 -> size (bytes): 1088
 -> SDNA index:   264
 ->      count:   1
 -> old pointer:  140732920679952
 
 [...]
 
Block: b'DNA1'
 -> size (bytes): 90688
 -> SDNA index:   0
 ->      count:   1
 -> old pointer:  4375110432
Begin DNA1: b'SDNA'
  4290x b'NAME'
     0 *next
     1 *prev
     2 *data
     3 *first
     4 *last
     5 x
     6 y
     7 z
     8 xmin
     9 xmax
     10 ymin
     11 ymax
     12 *pointer
     13 group
     14 val
     15 val2
     16 type
     17 subtype
     18 flag
     19 name[64]
     20 saved
     21 data
     22 len
     23 totallen
     24 *newid
     25 *lib
     
  [...]
  
  621x b'STRC'
     0 struct ('Link', 16)
       0: field *next :: ('Link', 16)
       1: field *prev :: ('Link', 16)
       Bytes padding:  0
     1 struct ('LinkData', 24)
       0: field *next :: ('LinkData', 24)
       1: field *prev :: ('LinkData', 24)
       2: field *data :: ('void', 0)
       Bytes padding:  0
     2 struct ('ListBase', 16)
       0: field *first :: ('void', 0)
       1: field *last :: ('void', 0)
       Bytes padding:  0
     3 struct ('vec2s', 4)
       0: field x :: ('short', 2)
       1: field y :: ('short', 2)
       Bytes padding:  0
     4 struct ('vec2f', 8)
       0: field x :: ('float', 4)
       1: field y :: ('float', 4)
       Bytes padding:  0

```
