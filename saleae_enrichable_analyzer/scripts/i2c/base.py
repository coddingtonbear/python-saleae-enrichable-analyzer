import logging
from typing import Optional

from saleae_enrichable_analyzer import EnrichableAnalyzer


logger = logging.getLogger(__name__)


class I2CAnalyzer(EnrichableAnalyzer):
    def __init__(self, *args, **kwargs):
        super(I2CAnalyzer, self).__init__(*args, **kwargs)

        self._packets = {}

    @classmethod
    def add_arguments(cls, parser):
        EnrichableAnalyzer.add_arguments(parser)
        parser.add_argument(
            'i2c_address',
            help='The device\'s I2C address as a base-2 integer.',
            type=lambda x: int(x, base=2),
        )

    def store_frame(
        self,
        packet_id,
        frame_index,
        frame_type,
        flags,
        value,
    ):
        if packet_id not in self._packets:
            self._packets[packet_id] = []

        if not any(
            f['frame_index'] == frame_index for f in self._packets[packet_id]
        ):
            self._packets[packet_id].append({
                'frame_index': frame_index,
                'frame_type': frame_type,
                'flags': flags,
                'value': value,
            })

    def get_packet_frames(self, packet_id):
        return sorted(
            self._packets.get(packet_id, []),
            key=lambda f: f['frame_index'],
        )

    def get_packet_length(self, packet_id):
        return len(self._packets[packet_id])

    def get_packet_frame_index(self, packet_id, frame_index):
        return list(
            map(
                lambda frame: frame['frame_index'],
                self.get_packet_frames(packet_id)
            )
        ).index(frame_index)

    def get_packet_nth_frame(self, packet_id, idx):
        return self.get_packet_frames(packet_id)[idx]

    def handle_marker(
        self,
        packet_id: Optional[int],
        frame_index: int,
        sample_count: int,
        start_sample: int,
        end_sample: int,
        frame_type: int,
        flags: int,
        value1: int,   # SPI: MOSI; I2C: SDA
        value2: int,   # SPI: MISO; I2C: Undefined
    ):
        # Data in I2C spread across multiple frames; we need to
        # gather data across all of those frames to have anything
        # meanintful to display.
        self.store_frame(
            packet_id,
            frame_index,
            frame_type,
            flags,
            value1,
        )

        return []

    def packet_address_matches(self, packet_id: Optional[int]):
        try:
            address_frame = self.get_packet_nth_frame(packet_id, 0)
        except IndexError:
            logger.debug(
                "Could not find address frame for packet %s",
                hex(packet_id)
            )
            return False

        if(address_frame['value'] >> 1 != self._address):
            # This isn't our device
            return False

        return True
