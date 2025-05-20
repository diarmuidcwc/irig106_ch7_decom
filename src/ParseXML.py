import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Tuple, Dict
import logging
from collections import defaultdict


@dataclass
class Location:
    offset_words: int
    occurrences: int


class XMLFile(object):
    def __init__(self, filename: str):
        self.filename: str = filename
        self.locations: Dict[int, List[Location]] = {}  # indexed by minor frame number
        self.ptfr_size_16b_words = 1
        self._parse_xidml()
        self.locations = self._optimize_locations()

    def _parse_xidml(self) -> None:
        tree = ET.parse(self.filename)
        root = tree.getroot()

        # Step 1: Find all ParameterReferences with VendorName="PTFR"
        param_ref = root.find(".//ParameterReference[@VendorName='PTFR']")
        param_name = param_ref.text.strip()

        param = root.find(f'.//Parameter[@Name="{param_name}"]')
        param_size_bits = int(param.find("SizeInBits").text)
        if param_size_bits % 16 != 0:
            raise Exception("PTFR parameter must be a multiple of 16bits")
        self.ptfr_size_16b_words = int(param_size_bits // 16)

        logging.debug(f"Found {param_name} with size in 16 words={self.ptfr_size_16b_words}")

        for mapping in root.findall(".//Mapping"):
            ref = mapping.find("ParameterReference")
            if ref is not None and ref.text and ref.text.strip() == param_name:
                for loc_elem in mapping.findall("Location"):
                    # Extract values and convert to int
                    minor_frame = int(loc_elem.findtext("MinorFrameNumber"))
                    offset_words = int(loc_elem.findtext("Offset_Words"))
                    occurrences = int(loc_elem.findtext("Occurrences"))
                    if minor_frame not in self.locations:
                        self.locations[minor_frame] = []
                    self.locations[minor_frame].append(Location(offset_words=offset_words, occurrences=occurrences))

        return None

    def _optimize_locations(self) -> Dict[int, List[Location]]:

        optimized_by_frame: Dict[int, List[Location]] = {}

        # Process each group
        for minor_frame, locs in self.locations.items():
            if not locs:
                optimized_by_frame[minor_frame] = []
                continue
            # Sort by offset_words
            sorted_locs = sorted(locs, key=lambda l: l.offset_words)
            optimized = []
            current = sorted_locs[0]

            for next_loc in sorted_locs[1:]:
                expected_offset = current.offset_words + current.occurrences
                if next_loc.offset_words == expected_offset:
                    # Extend the current range
                    current.occurrences += next_loc.occurrences
                else:
                    # Finalize the current and move on
                    optimized.append(current)
                    current = next_loc
            optimized.append(current)
            optimized_by_frame[minor_frame] = optimized

        return optimized_by_frame

    # Step 4: Extract parameter data from byte buffer based on mapping
    def extract_parameter_data(self, minorframe: int, buffer: bytes) -> bytes:
        extracted_bits = bytearray()
        if minorframe not in self.locations:
            return None

        for location in self.locations[minorframe]:
            byte_offset = location.offset_words * 2
            num_bytes = self.ptfr_size_16b_words * 2 * location.occurrences
            chunk = buffer[byte_offset : byte_offset + num_bytes]
            logging.debug(
                f"byte_offset={byte_offset} occ={location.occurrences} num_bytes={num_bytes} chunklen={len(chunk)}"
            )
            extracted_bits.extend(chunk)
        return bytes(extracted_bits)
