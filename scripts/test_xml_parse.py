import ParseXML
import logging
import argparse
import struct

logging.basicConfig(level=logging.INFO)


def create_parser():
    """
    Return a parser and arguments
    :return:
    """

    parser = argparse.ArgumentParser(description="parse a xidml for the PTRF parameter")
    parser.add_argument("--filename", required=True, type=str, help="the filename")
    return parser


def main(fname):

    xml = ParseXML.XMLFile(fname)
    fm_len = 2048
    test_buffer = struct.pack(f">{fm_len}H", *(list(range(fm_len))))  # mock 256-byte test buffer
    # print(repr(xml.locations))
    for mf in xml.locations.keys():
        data = xml.extract_parameter_data(mf, test_buffer)
        print(f" extracted data for minorframe={mf} len= {len(data)}")


# Example usage
if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    main(args.filename)
