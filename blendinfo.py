#!/usr/bin/env python3

import struct
import sys
from typing import List, Tuple, IO

TypeInf = Tuple[str, int]


class DNAField:
	def __init__(self, name: str, offset: int, typeinf: TypeInf, ptr_size: int):
		self.orig_name = name
		self.offset = offset
		self.typeinf = typeinf
		self.size = typeinf[1]
		self.dims = []
		while name.endswith("]"):
			openbrace = name.index('[')
			closebrace = name.index(']')
			dim = int(name[openbrace + 1:closebrace])
			self.dims.append(dim)
			self.size *= dim
			name = name[:openbrace] + name[closebrace + 1:]
		if name.startswith("*"):
			self.size = ptr_size
			self.is_ptr = True
		else:
			self.is_ptr = False

	def __str__(self):
		decl = "{:10} {}".format(self.typeinf[0], self.orig_name)
		return "{:32} // {:4} bytes, offset {}".format(decl, self.size, self.offset)


class DNAStruct:
	def __init__(self, name, size, fields: List[DNAField]):
		self.name = name
		self.size = size
		self.fields = fields
		self.is_id = len(fields) > 0 and fields[0].orig_name == "id"

	def __str__(self):
		return "struct {} // {} bytes{}".format(self.name, self.size, ", is ID" if self.is_id else "")


class BlendFile:
	def __init__(self, blend_file: IO):
		self.file = blend_file
		header = self.file.read(12)
		if not header.startswith(b'BLENDER'):
			raise ValueError("Not a .blend file (header: {}".format(header))
		self.PTR_SIZE = 4 if header[7] == b'_' else 8
		bigend = header[8] == b'V'
		self.PTR = 'Q' if self.PTR_SIZE == 8 else 'I'
		self.EF = '>' if bigend else '<'
		self.HEADER_SIZE = 16 + self.PTR_SIZE

	def __str__(self):
		return "Blend file: {}, {} bit pointers".format(
			"Big-endian" if self.EF == '>' else "Little-endian",
			self.PTR_SIZE * 8
		)

	def _unpack(self, fmt, data):
		return struct.unpack(self.EF + fmt, data)

	def _seek_after_header(self):
		self.file.seek(12, 0)

	def _all_block_headers(self):
		self._seek_after_header()
		while True:
			header = self.file.read(self.HEADER_SIZE)
			fmt = "4sI" + self.PTR + "II"
			block, size, oldp, idx, cnt = self._unpack(fmt, header)
			if block == b'ENDB':
				break
			yield block, size, oldp, idx, cnt

	def scan_dna(self) -> List[DNAStruct]:
		types = None
		for block, size, oldp, idx, cnt in self._all_block_headers():
			if block == b'DNA1':
				data = self.file.read(size)
				types = self._parse_dna1(data)
			else:
				self.file.seek(size, 1)
		if types is None:
			raise ValueError("No DNA1 block found")
		return types

	def count_id_content(self, dna_structs: List[DNAStruct]) -> Tuple[int, int, int, int, int, int]:
		ndatablocks, ndatablocks_total, nobjs, nobjs_total, nbytes, nbytes_total = 0, 0, 0, 0, 0, 0
		for block, size, oldp, idx, cnt in self._all_block_headers():
			self.file.seek(size, 1)
			ndatablocks_total += 1
			nobjs_total += cnt
			nbytes_total += size
			if idx == 0:
				continue
			if idx > len(dna_structs):
				print("Strange datablock", block, "references DNAStruct", idx)
				continue
			dna_struct = dna_structs[idx]
			if not dna_struct.is_id:
				continue
			ndatablocks += 1
			nobjs += cnt
			nbytes += cnt * dna_struct.size

		return ndatablocks, ndatablocks_total, nobjs, nobjs_total, nbytes, nbytes_total

	def _parse_dna1(self, data) -> List[DNAStruct]:
		data = data[4:]

		names = []
		types = []

		name, num = self._unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		for i in range(num):
			slen = data[ofs:].index(b'\000')
			name = data[ofs:ofs + slen].decode('ascii')
			names.append(name)
			ofs += slen + 1
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name, num = self._unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		for i in range(num):
			slen = data[ofs:].index(b'\000')
			name = data[ofs:ofs + slen].decode('ascii')
			types.append((name, 0))
			ofs += slen + 1
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name = self._unpack("4s", data[:4])
		data = data[4:]
		ofs = 0
		for i, (name, _) in enumerate(types):
			tlen = self._unpack("H", data[ofs:ofs + 2])[0]
			ofs += 2
			types[i] = (name, tlen)
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name, num = self._unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		dna_structs = []
		for i in range(num):
			typeidx, nfields = self._unpack("HH", data[ofs:ofs + 4])

			ofs += 4
			field_ofs = 0
			dna_fields = []
			for j in range(nfields):
				(field_typeidx, field_nameidx) = self._unpack("HH", data[ofs:ofs + 4])
				field_name = names[field_nameidx]
				dna_field = DNAField(field_name, field_ofs, types[field_typeidx], self.PTR_SIZE)
				dna_fields.append(dna_field)  #
				ofs += 4
				field_ofs += dna_field.size
			dna_struct = DNAStruct(types[typeidx][0], types[typeidx][1], dna_fields)
			dna_structs.append(dna_struct)
		return dna_structs


def parse_args():
	import argparse
	parser = argparse.ArgumentParser(description="Examines .blend files and prints information")
	parser.add_argument('blendfile', metavar='PATH', help=".blend file to examine", nargs=1)
	parser.add_argument("--info", action="store_true", help="Print information about the .blend file itself")
	parser.add_argument("--dna", action="store_true", help="Print detailed information about DNA structs")
	parser.add_argument("--id", action="store_true", help="Print summary on 'ID' structs")
	return parser.parse_args()


if __name__ == "__main__":
	try:
		args = parse_args()
	except Exception as e:
		print(e)
		sys.exit(2)

	for path in args.blendfile:
		with open(path, mode="r+b") as file:
			bf = BlendFile(file)
			if args.info:
				print(bf)
			if args.dna or args.id:
				dna_structs = bf.scan_dna()
			if args.dna:
				for i, s in enumerate(dna_structs):
					print("{} [#{}]".format(s, i))
					for f in s.fields:
						print("   ", f)
			if args.id:
				print("{} of {} datablocks containing {} of {} objects totalling {} of {} bytes are ID".format(
					*bf.count_id_content(dna_structs)))
