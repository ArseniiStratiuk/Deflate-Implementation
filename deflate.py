import argparse
import struct
from collections import Counter, defaultdict
from heapq import heappush, heappop
from tqdm import tqdm


class Codeword:
    """Represents an LZ77 compression codeword.

    Attributes:
        prefix_start_offset (int): Offset to the start of the matching prefix.
        prefix_len (int): Length of the matching prefix.
        character (int): Next character byte value following the match.
    """
    def __init__(self, prefix_start_offset, prefix_len, character):
        self.prefix_start_offset = prefix_start_offset
        self.prefix_len = prefix_len
        self.character = character

    def __repr__(self):
        return f"Codeword(offset={self.prefix_start_offset}, len={self.prefix_len}, char={self.character})"


class Lz77Compressor:
    """LZ77 compressor implementation with fixed window size.
    
    Args:
        sliding_window_length (int): Size of the sliding window in bytes.
        data (bytes): Input data to compress.
    """
    def __init__(self, sliding_window_length, data):
        self._sliding_window_length = sliding_window_length
        self._buffer = data

    def codeword_for_position(self, position):
        """Finds the best codeword for current position in buffer."""
        longest_match_len = 0
        longest_match_offset = 0
        max_offset = min(position, self._sliding_window_length)

        for offset in range(1, max_offset + 1):
            start = position - offset
            if start < 0:
                break
            current_match_len = 0
            while ((position + current_match_len < len(self._buffer)) and
                   (start + current_match_len < position) and
                   (self._buffer[start + current_match_len] == self._buffer[position + current_match_len])):
                current_match_len += 1
                if current_match_len >= 258:
                    break
            if current_match_len > longest_match_len:
                longest_match_len = current_match_len
                longest_match_offset = offset

        if longest_match_len > 0:
            next_char_pos = position + longest_match_len
            if next_char_pos >= len(self._buffer):
                return Codeword(0, 0, self._buffer[position])
            next_char = self._buffer[next_char_pos]
            return Codeword(longest_match_offset, longest_match_len, next_char)
        else:
            next_char = self._buffer[position]
            return Codeword(0, 0, next_char)

class Lz77:
    """Main LZ77 compression handler.
    
    Args:
        sliding_window_length (int): Size of the sliding window in bytes.
    """
    def __init__(self, sliding_window_length):
        self._sliding_window_length = sliding_window_length

    def compress(self, data):
        """Generates codewords for input data.
        
        Yields:
            Codeword: Compression codewords sequentially.
        """
        compressor = Lz77Compressor(self._sliding_window_length, data)
        position = 0
        while position < len(data):
            codeword = compressor.codeword_for_position(position)
            yield codeword
            position += codeword.prefix_len + 1

class Lz77Decompressor:
    """LZ77 decompression implementation.
    
    Args:
        window_size (int): Size of the sliding window used in compression.
    """
    def __init__(self, window_size):
        self.window_size = window_size
        self.buffer = bytearray()

    def decompress_codeword(self, codeword):
        """Processes a single codeword during decompression."""
        offset = codeword.prefix_start_offset
        length = codeword.prefix_len
        char = codeword.character

        if offset > 0:
            start = len(self.buffer) - offset
            for i in range(length):
                if start + i >= len(self.buffer):
                    break
                self.buffer.append(self.buffer[start + i])
        self.buffer.append(char)

    def get_data(self):
        """Retrieves decompressed data.
        
        Returns:
            bytes: Decompressed byte stream.
        """
        return bytes(self.buffer)

class Codec:
    """Huffman coding codec for encoding/decoding byte streams."""
    def __init__(self):
        self.letters = {}
        self.codes = {}

    def update(self, letter, code):
        """Updates codec with new encoding pair."""
        self.letters[code] = letter
        self.codes[letter] = code

    def encode(self, symbols):
        """Encodes a list of symbols to bitstring.
        
        Args:
            symbols (list): List of byte values to encode.
            
        Returns:
            str: Binary string of encoded data.
        """
        return ''.join(self.codes[s] for s in symbols)

    def decode(self, bitstream):
        """Decodes a bitstring to original symbols.
        
        Args:
            bitstream (str): Binary string of encoded data.
            
        Returns:
            list: Decoded byte values.
        """
        current_code = ''
        decoded = []
        for bit in bitstream:
            current_code += bit
            if current_code in self.letters:
                decoded.append(self.letters[current_code])
                current_code = ''
        return decoded


def huffman(frequencies):
    """Generates Huffman codes for given frequency distribution.
    
    Args:
        frequencies (dict): Byte value to frequency count mapping.
        
    Returns:
        dict: Byte value to binary code mapping.
    """
    heap = []
    for symbol, freq in frequencies.items():
        heappush(heap, (freq, [symbol]))

    codes = defaultdict(str)
    while len(heap) > 1:
        freq1, sym1 = heappop(heap)
        freq2, sym2 = heappop(heap)
        for s in sym1:
            codes[s] = '0' + codes[s]
        for s in sym2:
            codes[s] = '1' + codes[s]
        heappush(heap, (freq1 + freq2, sym1 + sym2))

    if len(frequencies) == 1:
        codes[next(iter(frequencies))] = '0'
    return codes


def compress_file(input_path, output_path):
    """Compresses file using LZ77 + Huffman coding.
    
    Args:
        input_path (str): Path to input file.
        output_path (str): Path for output .deflate file.
    """
    with open(input_path, 'rb') as f:
        data = f.read()

    lz = Lz77(32768)
    codeword_generator = lz.compress(data)
    codewords = []
    position = 0

    with tqdm(total=len(data), desc="LZ77 Compressing") as pbar:
        while position < len(data):
            codeword = next(codeword_generator)
            codewords.append(codeword)
            step = codeword.prefix_len + 1
            position += step
            pbar.update(step)

    serialized = bytearray()
    for cw in codewords:
        serialized += struct.pack('>HHB', cw.prefix_start_offset, 
                                cw.prefix_len, cw.character)

    symbols = [bytes([b]) for b in serialized]
    freq = Counter(symbols)

    codes = huffman(freq) if freq else {}
    codec = Codec()
    for sym, code in codes.items():
        codec.update(sym, code)

    encoded_bits = codec.encode(symbols) if codes else ''
    padding = (8 - (len(encoded_bits) % 8)) % 8
    encoded_bits += '0' * padding

    bytes_out = bytearray()
    for i in range(0, len(encoded_bits), 8):
        byte = encoded_bits[i:i+8]
        bytes_out.append(int(byte, 2))

    with open(output_path, 'wb') as f_out:
        for b in range(256):
            byte_key = bytes([b])
            count = freq.get(byte_key, 0)
            f_out.write(count.to_bytes(4, 'big'))
        f_out.write(bytes_out)

def decompress_file(input_path, output_path):
    """Decompresses .deflate file to original content.
    
    Args:
        input_path (str): Path to .deflate file.
        output_path (str): Path for decompressed output.
    """
    with open(input_path, 'rb') as f:
        freq_data = f.read(1024)
        encoded_data = f.read()

    freq = {}
    for b in range(256):
        count = int.from_bytes(freq_data[b*4:(b+1)*4], 'big')
        if count > 0:
            freq[bytes([b])] = count

    codes = huffman(freq) if freq else {}
    codec = Codec()
    for sym, code in codes.items():
        codec.update(sym, code)

    bitstream = ''.join(f"{byte:08b}" for byte in encoded_data)
    decoded_symbols = codec.decode(bitstream) if codes else []
    serialized = b''.join(decoded_symbols) if codes else b''

    codewords = []
    for i in range(0, len(serialized), 5):
        chunk = serialized[i:i+5]
        if len(chunk) != 5:
            break
        offset, length, char = struct.unpack('>HHB', chunk)
        codewords.append(Codeword(offset, length, char))

    decompressor = Lz77Decompressor(32768)
    for cw in tqdm(codewords, desc="Decompressing"):
        decompressor.decompress_codeword(cw)

    with open(output_path, 'wb') as f_out:
        f_out.write(decompressor.get_data())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEFLATE Compression/Decompression")
    subparsers = parser.add_subparsers(dest='command')

    compress_parser = subparsers.add_parser('compress')
    compress_parser.add_argument('input')
    compress_parser.add_argument('output')

    decompress_parser = subparsers.add_parser('decompress')
    decompress_parser.add_argument('input')
    decompress_parser.add_argument('output')

    args = parser.parse_args()

    if args.command == 'compress':
        compress_file(args.input, args.output)
    elif args.command == 'decompress':
        decompress_file(args.input, args.output)
