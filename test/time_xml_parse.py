import timeit


setup = """
import ParseXML
import struct

xml = ParseXML.XMLFile("xml/free_as_ch7.xidml")
test_buffer = struct.pack(">2048H", *(list(range(2048)))) 
"""
runs = 10000
ti = timeit.timeit("xml.extract_parameter_data(1, test_buffer)", number=runs, setup=setup)
print(f"Iterations per second = {1/(ti/runs)}")
