#!/usr/bin/env python3

import struct
import sys
from typing import List, Tuple, Dict, IO

TypeInf = Tuple[str, int]
Pointers = List[int]
DNATypes: object = Dict[int, Tuple[TypeInf, Pointers]]

def debug(*args):
	pass
	#print(*args)

def scan_dna(file: IO) -> DNATypes:
	while True:
		header = file.read(HEADER_SIZE)
		fmt = EF + "4sI" + PTR + "II"
		block, size, oldp, idx, cnt = struct.unpack(fmt, header)
		if header[0:4] == b'ENDB':
			break
		data = file.read(size)
		if header[0:4] == b'DNA1':
			types: DNATypes = parse_dna1(data)
	if types is None:
		raise ValueError("No DNA1 block found")
	return types

def parse_dna1(data) -> DNATypes:
	debug("Begin DNA1:", data[:4])
	assert data[:4] == b'SDNA'
	data = data[4:]

	names = []
	types = []

	name, num = struct.unpack("4sI", data[:8])
	#debug("  {}x {}".format(num, name))
	assert name == b'NAME'
	data = data[8:]
	ofs = 0
	for i in range(num):
		slen = data[ofs:].index(b'\000')
		name = data[ofs:ofs + slen].decode('ascii')
		names.append(name)
		ofs += slen + 1
		#debug("    ", i, name)
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]

	name, num = struct.unpack("4sI", data[:8])
	assert name == b'TYPE'
	#debug("  {}x {}".format(num, name))
	data = data[8:]
	ofs = 0
	for i in range(num):
		slen = data[ofs:].index(b'\000')
		name = data[ofs:ofs + slen].decode('ascii')
		types.append((name, 0))
		ofs += slen + 1
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]

	(name,) = struct.unpack("4s", data[:4])
	assert name == b'TLEN'
	#debug("  {}x {}".format(len(types), name))
	data = data[4:]
	ofs = 0
	for i, (name, _) in enumerate(types):
		tlen = struct.unpack("H", data[ofs:ofs + 2])[0]
		ofs += 2
		types[i] = (name, tlen)
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]

	#debug("   -> Types:")
	#for i, (name, tlen) in enumerate(types):
	#	debug("      {}: {} ({} bytes)".format(i, name, tlen))

	name, num = struct.unpack("4sI", data[:8])
	#debug("  {}x {}".format(num, name))
	assert name == b'STRC'
	data = data[8:]
	ofs = 0
	result_types = {}
	for i in range(num):
		typeidx, nfields = struct.unpack("HH", data[ofs:ofs + 4])
		debug("    ", i, "struct", types[typeidx])
		ofs += 4
		result_pointers = []
		result_types[i] = (types[typeidx], result_pointers)
		ofs_in_struct = 0
		for j in range(nfields):
			(field_typeidx, field_nameidx) = struct.unpack("HH", data[ofs:ofs + 4])
			field_name = names[field_nameidx]
			if '*' in field_name:
				field_bytes = PTR_SIZE
				result_pointers.append(ofs_in_struct)
				debug("      ptr @ {}".format(ofs_in_struct))
			else:
				field_bytes = types[field_typeidx][1]
				while field_name.endswith(']'):
					openbrace = field_name.index('[')
					closebrace = field_name.index(']')
					array_size = int(field_name[openbrace + 1:closebrace])
					field_bytes *= array_size
					field_name = field_name[closebrace + 1:]
			ofs_in_struct += field_bytes
			ofs += 4
			debug("       {}: field {} :: {}".format(j, field_name, types[field_typeidx]))
	# 4-byte alignment
	data = data[(ofs + 3) // 4 * 4:]

	debug("  Bytes left:", len(data))
	return result_types


def replace_pointers(file: IO, types: DNATypes, restore_from: IO, extract_to: IO):
	file.seek(12, 0)  # Back to beginning
	while True:
		block, size = struct.unpack(EF + "4sI", file.read(8))

		old_ptr = file.read(PTR_SIZE)
		if restore_from is not None:
			file.seek(-PTR_SIZE, 1)
			file.write(restore_from.read(PTR_SIZE))
		if extract_to is not None:
			extract_to.write(old_ptr)

		idx, cnt = struct.unpack(EF + "II", file.read(8))

		debug("{}: {} bytes ({} x #{})".format(block, size, cnt, idx))

		if block == b'ENDB':
			break
		elif block == b'DNA1':
			file.seek(size, 1)
		else:
			oldpos = file.tell()
			if idx == 0:
				debug("  Skipping type with SDNA idx 0")
				data = file.read(size)
				debug("    Content:", data)
				continue
			pos = 0
			assert idx in types

			typeinf, pointers = types[idx]
			debug("  This is a", typeinf)
			assert typeinf[1] * cnt == size and idx != 0
			for p in pointers:
				file.seek(p - pos, 1)

				old_ptr = file.read(PTR_SIZE)
				if restore_from is not None:
					file.seek(-PTR_SIZE, 1)
					file.write(restore_from.read(PTR_SIZE))
				if extract_to is not None:
					extract_to.write(old_ptr)

				pos = p + PTR_SIZE

			file.seek(size - pos, 1)
			assert oldpos + size == file.tell()


def read_globals(file: IO):
	global PTR_SIZE, PTR, EF, HEADER_SIZE
	header = file.read(12)
	debug("Header:", header)
	PTR_SIZE = 4 if header[7] == b'_' else 8
	bigend = header[8] == b'V'
	debug(" -> pointer size:", PTR_SIZE)
	debug(" -> big endian:  ", bigend)
	PTR = 'Q' if PTR_SIZE == 8 else 'I'
	EF = '>' if bigend else '<'
	HEADER_SIZE = 16 + PTR_SIZE

def parse_args():
	import argparse
	parser = argparse.ArgumentParser(description="Modifies .blend files so that memory addresses are zeroed and saved externally")
	parser.add_argument('--blendfile', metavar='PATH', help=".blend file to modify", required=True)
	parser.add_argument('--restore-from', metavar='PATH', help="file from wich to restore pointers in .blend file", required=False)
	parser.add_argument('--extract-to', metavar='PATH', help="file into wich to extract pointers in .blend file", required=False)
	return parser.parse_args()

if __name__ == "__main__":
	try:
		args = parse_args()
	except Exception as e:
		print(e)
		sys.exit(2)

	restore_from = None
	if args.restore_from is not None:
		restore_from = open(args.restore_from, "rb")

	extract_to = None
	if args.extract_to is not None:
		extract_to = open(args.extract_to, "wb")

	with open(args.blendfile, mode="r+b") as file:
		read_globals(file)
		types = scan_dna(file)
		replace_pointers(file, types, restore_from, extract_to)

