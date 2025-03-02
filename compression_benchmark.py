import time
import subprocess
import matplotlib.pyplot as plt
import os

from deflate import compress_file, decompress_file

def generate_test_files():
    sizes = [1, 100, 1000]  # KB
    types = ['text', 'binary']
    
    for file_type in types:
        os.makedirs(file_type, exist_ok=True)
        for size in sizes:
            path = f"{file_type}/{size}KB.dat"
            if os.path.exists(path):
                continue
                
            with open(path, 'wb') as f:
                if file_type == 'text':
                    data = b'A' * (size * 1024)
                else:
                    data = os.urandom(size * 1024)
                f.write(data)

def run_benchmark():
    tools = ['custom', 'gzip']
    results = {tool: {'time': [], 'ratio': []} for tool in tools}
    
    for file_type in ['text', 'binary']:
        for size in [1, 100, 1000]:
            input_path = os.path.join(os.path.dirname(__file__), f"{file_type}/{size}KB.dat")
            compressed_path = f"{file_type}/{size}KB.compressed"
            decompressed_path = f"{file_type}/{size}KB.decompressed"
            
            start = time.time()
            compress_file(input_path, compressed_path)
            compress_time = time.time() - start
            decompress_file(compressed_path, decompressed_path)
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(compressed_path)
            results['custom']['time'].append(compress_time)
            results['custom']['ratio'].append(compressed_size/original_size)
            
            start = time.time()
            subprocess.run(['gzip', '-k', '-f', input_path])
            compress_time = time.time() - start
            subprocess.run(['gzip', '-d', f"{input_path}.gz"])
            compressed_size = os.path.getsize(f"{input_path}.gz")
            results['gzip']['time'].append(compress_time)
            results['gzip']['ratio'].append(compressed_size/original_size)
            
    return results

def plot_results(results):
    sizes = ['1KB', '100KB', '1MB']
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    for tool in ['custom', 'gzip']:
        ax1.plot(sizes, results[tool]['time'], label=tool)
    ax1.set_title('Compression Time Comparison')
    ax1.set_ylabel('Seconds')
    ax1.legend()
    
    for tool in ['custom', 'gzip']:
        ax2.plot(sizes, results[tool]['ratio'], label=tool)
    ax2.set_title('Compression Ratio Comparison')
    ax2.set_ylabel('Compressed/Original')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('benchmark.png')
    plt.show()

if __name__ == "__main__":
    generate_test_files()
    results = run_benchmark()
    plot_results(results)
