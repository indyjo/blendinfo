#!/usr/bin/env python3

import struct
import sys
from typing import List, IO, Union

from blendinfo import DNAStruct, BlendFile


class StripBlendFile(BlendFile):
	def __init__(self, file: IO):
		BlendFile.__init__(self, file)

	def replace_pointers(
		self,
		dna_structs: List[DNAStruct],
		restore_from: Union[IO[bytes], None],
		extract_to: Union[IO[bytes], None],
	) -> None:
		idx_by_name: dict[str, int] = {}
		for idx, ds in enumerate(dna_structs):
			idx_by_name[ds.name] = idx

		for block, size, oldp, idx, cnt in self._all_block_headers():
			if restore_from is not None:
				(newp,) = self.unpack(self.PTR, restore_from.read(self.PTR_SIZE))
				new_header = self.pack("4sI" + self.PTR + "II", block, size, newp, idx, cnt)
				self.file.seek(-len(new_header), 1)
				self.file.write(new_header)
			if extract_to is not None:
				extract_to.write(self.pack(self.PTR, oldp))

			if idx == 0:
				self.file.seek(size, 1)
				continue

			ds = dna_structs[idx]
			assert ds.size * cnt == size

			# Helper function to recursively overwrite pointers in a struct
			def replace_in_struct(ds: DNAStruct, data: bytes, begin: int):
				for f in ds.fields:
					if f.is_ptr:
						if extract_to is not None:
							extract_to.write(data[begin + f.offset:begin + f.offset + f.size])
						if restore_from is not None:
							data[begin + f.offset:begin + f.offset + f.size] = restore_from.read(self.PTR_SIZE)
						continue
					if not f.typeinf[0] in idx_by_name:
						continue
					field_struct = dna_structs[idx_by_name[f.typeinf[0]]]
					replace_in_struct(field_struct, data, begin + f.offset)

			# Iterate over all structs in this datablock. Write back to file.
			for i in range(0, cnt):
				data = self.file.read(ds.size)
				origdata = data
				if restore_from is not None:
					data = bytearray(data)
				replace_in_struct(ds, data, 0)
				if restore_from is not None:
					self.file.seek(-ds.size, 1)
					self.file.write(data)

def parse_args():
	import argparse
	parser = argparse.ArgumentParser(
		description="Modifies .blend files so that memory addresses are zeroed and saved externally")
	parser.add_argument('--blendfile', metavar='PATH', help=".blend file to modify", required=True)
	parser.add_argument('--restore-from', metavar='PATH', help="file from wich to restore pointers in .blend file",
	                    required=False)
	parser.add_argument('--extract-to', metavar='PATH', help="file into wich to extract pointers in .blend file",
	                    required=False)
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
		bf = StripBlendFile(file)
		types = bf.scan_dna()
		bf.replace_pointers(types, restore_from, extract_to)
