#!/usr/bin/env python3

import sys, struct

def read_dna1(data):
	print("Begin DNA1:", data[:4])
	data = data[4:]
	
	names=[]
	types=[]
	
	name, num = struct.unpack("4sI", data[:8])
	print("  {}x {}".format(num, name))
	data = data[8:]
	ofs = 0
	for i in range(num):
		slen = data[ofs:].index(b'\000')
		name = data[ofs:ofs+slen].decode('ascii')
		names.append(name)
		ofs += slen + 1
		print("    ", i,  name)
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]
		
	name, num = struct.unpack("4sI", data[:8])
	print("  {}x {}".format(num, name))
	data = data[8:]
	ofs = 0
	for i in range(num):
		slen = data[ofs:].index(b'\000')
		name = data[ofs:ofs+slen].decode('ascii')
		types.append( (name, 0) )
		ofs += slen + 1
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]
	
	name = struct.unpack("4s", data[:4])
	print("  {}x {}".format(len(types), name))
	data = data[4:]
	ofs = 0
	for i, (name, _) in enumerate(types):
		tlen = struct.unpack("H", data[ofs:ofs+2])[0]
		ofs += 2
		types[i] = (name, tlen)
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]
	
	print("   -> Types:")
	for i, (name, tlen) in enumerate(types):
		print("      {}: {} ({} bytes)".format(i, name, tlen))

	name, num = struct.unpack("4sI", data[:8])
	print("  {}x {}".format(num, name))
	data = data[8:]
	ofs = 0
	for i in range(num):
		typeidx, nfields = struct.unpack("HH", data[ofs:ofs+4])
		print("    ", i, "struct", types[typeidx])
		ofs += 4
		fields_bytes = 0
		for j in range(nfields):
			(field_typeidx,field_nameidx) = struct.unpack("HH", data[ofs:ofs+4])
			ofs += 4
			field_name = names[field_nameidx]
			orig_field_name = field_name
			field_bytes = 8 if field_name.startswith('*') else types[field_typeidx][1]
			while field_name.endswith(']'):
				openbrace = field_name.index('[')
				closebrace = field_name.index(']')
				array_size = int(field_name[openbrace+1:closebrace])
				field_bytes *= array_size
				field_name = field_name[:openbrace] + field_name[closebrace+1:]
			print("       {:>3} @ {:>5}: field {:16} :: {}".format(j, fields_bytes, orig_field_name, str(types[field_typeidx])))
			fields_bytes += field_bytes
		print("       Bytes padding: ", types[typeidx][1] - fields_bytes)
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]
	
	print("  Bytes left:", len(data))
	
	print("End DNA1")

file = open(sys.argv[1], mode="rb")

header = file.read(12)
print("Header:", header)

PTR_SIZE = 4 if header[7] == b'_' else 8
bigend = header[8] == b'V'
print(" -> pointer size:", PTR_SIZE)
print(" -> big endian:  ", bigend)

nblocks = 0
sizesum = 0
while True:
	header = file.read(16 + PTR_SIZE)
	nblocks += 1
	print("Block:", header[0:4])
	size, oldp, idx, cnt = struct.unpack(('>' if bigend else '<') + "xxxxI" + ('Q' if PTR_SIZE == 8 else 'I') + "II", header)
	sizesum += size
	print(" -> size (bytes):", size)
	print(" -> SDNA index:  ", idx)
	print(" ->      count:  ", cnt)
	print(" -> old pointer: ", oldp)
	if header[0:4] == b'ENDB':
		break
	data = file.read(size)
	if header[0:4] == b'DNA1':
		read_dna1(data)
	
print("Blocks read:                       ", nblocks)
print("Bytes read (incl. 12 bytes header):", sizesum + 12)
