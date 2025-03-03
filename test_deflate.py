import unittest
import os
import tempfile
import struct
import random
from deflate import Codeword, Lz77Compressor, Lz77Decompressor, Codec, huffman, compress_file, decompress_file

class TestDeflate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_files = []
        cls.temp_dir = tempfile.TemporaryDirectory()
        
        # Create test files
        cls.empty_file = os.path.join(cls.temp_dir.name, "empty.txt")
        open(cls.empty_file, 'wb').close()
        
        cls.single_byte_file = os.path.join(cls.temp_dir.name, "single.txt")
        with open(cls.single_byte_file, 'wb') as f:
            f.write(b'X')
            
        cls.text_file = os.path.join(cls.temp_dir.name, "text.txt")
        with open(cls.text_file, 'wb') as f:
            f.write(b"Hello World! " * 1000)
            
        cls.binary_file = os.path.join(cls.temp_dir.name, "binary.dat")
        with open(cls.binary_file, 'wb') as f:
            f.write(bytes([random.randint(0, 255) for _ in range(10000)]))

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_empty_file(self):
        compressed = os.path.join(self.temp_dir.name, "empty.deflate")
        decompressed = os.path.join(self.temp_dir.name, "empty.out")
        
        compress_file(self.empty_file, compressed)
        decompress_file(compressed, decompressed)
        
        self.assertEqual(os.path.getsize(decompressed), 0)

    def test_single_byte(self):
        compressed = os.path.join(self.temp_dir.name, "single.deflate")
        decompressed = os.path.join(self.temp_dir.name, "single.out")
        
        compress_file(self.single_byte_file, compressed)
        decompress_file(compressed, decompressed)
        
        with open(decompressed, 'rb') as f:
            self.assertEqual(f.read(), b'X')

    def test_text_file_roundtrip(self):
        compressed = os.path.join(self.temp_dir.name, "text.deflate")
        decompressed = os.path.join(self.temp_dir.name, "text.out")
        
        compress_file(self.text_file, compressed)
        decompress_file(compressed, decompressed)
        
        with open(self.text_file, 'rb') as orig, open(decompressed, 'rb') as dec:
            self.assertEqual(orig.read(), dec.read())

    def test_binary_file_roundtrip(self):
        compressed = os.path.join(self.temp_dir.name, "binary.deflate")
        decompressed = os.path.join(self.temp_dir.name, "binary.out")
        
        compress_file(self.binary_file, compressed)
        decompress_file(compressed, decompressed)
        
        with open(self.binary_file, 'rb') as orig, open(decompressed, 'rb') as dec:
            self.assertEqual(orig.read(), dec.read())

    def test_lz77_compression(self):
        data = b"ABABABACABABABAB"
        compressor = Lz77Compressor(32, data)
        
        # Test position 0 (first character)
        cw = compressor.codeword_for_position(0)
        self.assertEqual(cw.prefix_start_offset, 0)
        self.assertEqual(cw.prefix_len, 0)
        self.assertEqual(cw.character, ord('A'))

        # Test position 1 (new character)
        cw = compressor.codeword_for_position(1)
        self.assertEqual(cw.prefix_start_offset, 0)  # No match available
        self.assertEqual(cw.prefix_len, 0)
        self.assertEqual(cw.character, ord('B'))

    def test_lz77_decompression(self):
        decompressor = Lz77Decompressor(32)
        codewords = [
            Codeword(0, 0, ord('A')),  # A
            Codeword(1, 3, ord('B')),  # Copy 3 from 1 back (A), add B → AABBB
            Codeword(4, 4, ord('C'))   # Copy 4 from 4 back (BBBA), add C → AABBBABBAC
        ]

        for cw in codewords:
            decompressor.decompress_codeword(cw)

        result = decompressor.get_data()
        self.assertEqual(result, b'AAAABAAABC')

    def test_huffman_encoding(self):
        frequencies = {b'A': 5, b'B': 2, b'C': 1}
        codes = huffman(frequencies)
        
        # Verify codes are prefix-free
        code_list = list(codes.values())
        for i in range(len(code_list)):
            for j in range(i+1, len(code_list)):
                self.assertFalse(
                    code_list[i].startswith(code_list[j]) or 
                    code_list[j].startswith(code_list[i]),
                    f"Codes {code_list[i]} and {code_list[j]} are not prefix-free"
                )

    def test_codec_roundtrip(self):
        codec = Codec()
        codec.update(b'A', '0')
        codec.update(b'B', '10')
        codec.update(b'C', '11')
        
        original = [b'A', b'B', b'C', b'A', b'A']
        encoded = codec.encode(original)
        decoded = codec.decode(encoded)
        
        self.assertEqual(encoded, '0101100')
        self.assertEqual(decoded, original)

    def test_codeword_serialization(self):
        original = Codeword(123, 45, 67)
        packed = struct.pack('>HHB', original.prefix_start_offset, 
                           original.prefix_len, original.character)
        unpacked = struct.unpack('>HHB', packed)
        
        self.assertEqual(unpacked, (123, 45, 67))

if __name__ == '__main__':
    unittest.main()
