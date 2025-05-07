#!/usr/bin/env python3

import struct
import sys
from typing import List, Tuple, IO, Dict

TypeInf = Tuple[str, int]


class DNAField:
	def __init__(self, name: str, offset: int, typeinf: TypeInf, ptr_size: int):
		self.orig_name = name
		self.offset = offset
		self.typeinf = typeinf
		self.size = typeinf[1]
		self.dims: list[int] = []
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
	def __init__(self, name: str, size: int, fields: List[DNAField]):
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

	def unpack(self, fmt, data):
		return struct.unpack(self.EF + fmt, data)

	def pack(self, fmt, *values):
		return struct.pack(self.EF + fmt, *values)

	def _seek_after_header(self):
		self.file.seek(12, 0)

	def _all_block_headers(self):
		block: bytes
		size: int
		oldp: int
		idx: int
		cnt: int
		self._seek_after_header()
		while True:
			header = self.file.read(self.HEADER_SIZE)
			fmt = "4sI" + self.PTR + "II"
			block, size, oldp, idx, cnt = self.unpack(fmt, header)
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

	def dump_dot_graph(self, dna_structs: List[DNAStruct]):
		print("digraph blend_file {")
		# excludes = ['MTexPoly', 'MPoly', 'MLoopUV', 'MVert', 'MEdge', 'MLoop', "ARegion", "MDeformVert",
		#            "IDProperty", "bNodeSocket", "CustomDataLayer"]
		excludes = []
		idx_by_name = {}
		for idx, ds in enumerate(dna_structs):
			idx_by_name[ds.name] = idx

		objects = {}
		for block, size, oldp, idx, cnt in self._all_block_headers():
			self.file.seek(size, 1)
			id = "_{:x}".format(oldp)
			if idx > 0:
				ds = dna_structs[idx]
				if ds.name in excludes or ds.fields[0].orig_name != "id":
					continue
				label = ds.name
			else:
				continue
				label = "{} of size {}".format(block.decode('ascii'), size)
			objects[oldp] = True
			if cnt > 1:
				label = "{} x {}".format(cnt, label)
			print('  {} [label="{}"];'.format(id, label))

		print(" // -------------- Edges --------------")

		def dump_edges(data, ds: DNAStruct):
			for f in ds.fields:
				if f.is_ptr:
					if f.typeinf[0] in excludes:
						continue
					(tgtp,) = struct.unpack(self.EF + self.PTR, data[f.offset:f.offset + self.PTR_SIZE])
					if tgtp != 0 and tgtp in objects:
						tgt_id = "_{:x}".format(tgtp)
						print('  {} -> {} [label="{}"]; // {}'.format(id, tgt_id, f.orig_name, f.typeinf))
					continue
				if f.typeinf[0] not in idx_by_name:
					continue
				ds_field = dna_structs[idx_by_name[f.typeinf[0]]]
				dump_edges(data[f.offset:f.offset + f.size], ds_field)

		for block, size, oldp, idx, cnt in self._all_block_headers():
			if idx == 0:
				self.file.seek(size, 1)
				continue
			ds = dna_structs[idx]
			if ds.name in excludes or ds.fields[0].orig_name != "id":
				self.file.seek(size, 1)
				continue
			print("  // {} x {}".format(ds.name, cnt))
			data = self.file.read(size)
			id = "_{:x}".format(oldp)
			dump_edges(data, ds)

		print("}")

	def size_stats(self, dna_structs: List[DNAStruct]) -> List[Tuple[str, int]]:
		accum = {}
		for block, size, oldp, idx, cnt in self._all_block_headers():
			self.file.seek(size, 1)
			if idx > 0:
				key = dna_structs[idx].name
			else:
				key = block.decode('ascii')
			if not key in accum:
				accum[key] = (0, 0)
			s, c = accum[key]
			s += size
			c += cnt
			accum[key] = (s, c)

		return sorted(accum.items(), key=lambda v: v[1][0])

	def _dump_object(self, data: bytes, ds: DNAStruct, dna_structs: List[DNAStruct], idx_by_name: Dict[str, int],
	                 indent=""):
		print("{{ // {} bytes".format(ds.size))
		for f in ds.fields:
			ftype = f.typeinf[0]
			field_data = data[f.offset:f.offset + f.size]
			print("{}  {} {}".format(indent, ftype, f.orig_name), end='')
			if not f.is_ptr and ftype == "char" and len(f.dims) == 1:
				# char array
				s = data[f.offset:f.offset + min(f.size, 128)]
				if b'\x00' in s:
					s = s[:s.index(b'\x00')]
				print(" = {}{}".format(s, " // + {} bytes ".format(f.size - len(s))) if len(s) < f.size else "")
				continue
			if not f.is_ptr and len(f.dims) > 0:
				print(" // {} bytes".format(f.size))
				continue

			print(" = ", end='')
			if f.is_ptr:
				print("{:x}".format(self.unpack(self.PTR, field_data)[0]))
			elif ftype in idx_by_name:
				field_ds = dna_structs[idx_by_name[ftype]]
				self._dump_object(field_data, field_ds, dna_structs, idx_by_name, indent + "  ")
			elif ftype == 'int':
				print(self.unpack('i', field_data)[0])
			elif ftype == 'char':
				print(self.unpack('c', field_data)[0])
			elif ftype == 'short':
				print(self.unpack('h', field_data)[0])
			elif ftype == 'float':
				print(self.unpack('f', field_data)[0])
			elif ftype == 'double':
				print(self.unpack('d', field_data)[0])
			else:
				print("// {} bytes".format(f.size))
		print(indent + "}")

	def find_address(self, addr, dna_structs: List[DNAStruct]):
		for block, size, oldp, idx, cnt in self._all_block_headers():
			if addr < oldp or addr > oldp + size:
				self.file.seek(size, 1)
				continue

			if idx == 0:
				print("Found address {:x} in {} block of size {} at {:x}".format(
					addr, block, size, oldp,
				))
				break

			ds = dna_structs[idx]
			print("Found address {:x} in {} block of size {} at {:x} containing {} {} of size {}".format(
				addr, block, size, oldp, cnt, ds.name, ds.size
			))
			offset = addr - oldp
			offset_in_obj = offset % ds.size
			object_base = offset - offset_in_obj

			file.seek(object_base, 1)
			data = file.read(ds.size)
			file.seek(size - object_base - ds.size)

			idx_by_name = {}
			for _idx, _ds in enumerate(dna_structs):
				idx_by_name[_ds.name] = _idx
			self._dump_object(data, ds, dna_structs, idx_by_name)
			break

	def dump_all(self, dna_structs: List[DNAStruct]):
		idx_by_name = {}
		for _idx, _ds in enumerate(dna_structs):
			idx_by_name[_ds.name] = _idx

		for block, size, oldp, idx, cnt in self._all_block_headers():
			if idx == 0:
				print("{} block of size {} at {:x}".format(block, size, oldp))
				maxbytes = 64
				data = self.file.read(min(size, maxbytes))
				if b'\000' in data:
					data = data[:data.index(b'\000')]
				print(" ", data)
				if size > len(data):
					print("  [ ...", size - len(data), "more bytes ... ]")

				if size > maxbytes:
					self.file.seek(size - maxbytes, 1)
				continue

			ds = dna_structs[idx]
			print("{} block of size {} at {:x} containing {} objects of type {}".format(block, size, oldp, cnt,
			                                                                            ds.name))
			assert cnt * ds.size == size
			for i in range(0, cnt):
				data = self.file.read(ds.size)
				print("  #{} = ".format(i), end='')
				self._dump_object(data, ds, dna_structs, idx_by_name, "  ")

	def _parse_dna1(self, data: bytes) -> List[DNAStruct]:
		data = data[4:]

		names: list[str] = []
		types: list[TypeInf] = []

		name, num = self.unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		for i in range(num):
			slen = data[ofs:].index(b'\000')
			name = data[ofs:ofs + slen].decode('ascii')
			names.append(name)
			ofs += slen + 1
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name, num = self.unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		for i in range(num):
			slen = data[ofs:].index(b'\000')
			name = data[ofs:ofs + slen].decode('ascii')
			types.append((name, 0))
			ofs += slen + 1
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name = self.unpack("4s", data[:4])
		data = data[4:]
		ofs = 0
		for i, (name, _) in enumerate(types):
			tlen = self.unpack("H", data[ofs:ofs + 2])[0]
			ofs += 2
			types[i] = (name, tlen)
		# 4-byte alignment
		data = data[(ofs + 3) // 4 * 4:]

		name, num = self.unpack("4sI", data[:8])
		data = data[8:]
		ofs = 0
		dna_structs: list[DNAStruct] = []
		for i in range(num):
			typeidx, nfields = self.unpack("HH", data[ofs:ofs + 4])

			ofs += 4
			field_ofs = 0
			dna_fields = []
			for j in range(nfields):
				(field_typeidx, field_nameidx) = self.unpack("HH", data[ofs:ofs + 4])
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
	parser.add_argument("--dump", action="store_true", help="Print contents of all contained DNA data")
	parser.add_argument("--id", action="store_true", help="Print summary on 'ID' structs")
	parser.add_argument("--dot", action="store_true", help="Print dot graph fo whole file")
	parser.add_argument("--size", action="store_true", help="Print statistic on size claimed by data types")
	parser.add_argument("--find", metavar="ADDR", help="Finds the given address in the file's data")
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

			dna_structs = None
			if args.dna or args.dump or args.id or args.dot or args.size or args.find != None:
				dna_structs = bf.scan_dna()

			if args.dna:
				assert dna_structs is not None
				for i, s in enumerate(dna_structs):
					print("{} [#{}]".format(s, i))
					for f in s.fields:
						print("   ", f)

			if args.dump:
				assert dna_structs is not None
				bf.dump_all(dna_structs)

			if args.id:
				assert dna_structs is not None
				print("{} of {} datablocks containing {} of {} objects totalling {} of {} bytes are ID".format(
					*bf.count_id_content(dna_structs)))

			if args.dot:
				assert dna_structs is not None
				bf.dump_dot_graph(dna_structs)

			if args.size:
				assert dna_structs is not None
				for k, v in bf.size_stats(dna_structs):
					s, c = v
					print("  {:24} : {:9} bytes in {} objects".format(k, s, c))

			if args.find != None:
				assert dna_structs is not None
				addr = int(args.find, 16)
				bf.find_address(addr, dna_structs)
