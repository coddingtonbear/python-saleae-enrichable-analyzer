import logging
import sys
from typing import List, Optional

from saleae_enrichable_analyzer import Channel

from .base import I2CAnalyzer


logger = logging.getLogger(__name__)


class AD7995Analyzer(I2CAnalyzer):
    def __init__(self, cli_args, *args, **kwargs):
        super(AD7995Analyzer, self).__init__(cli_args, *args, **kwargs)

        self._address = cli_args.i2c_address
        self._bits = cli_args.bits
        self._reference_voltage = cli_args.reference_voltage

    @classmethod
    def add_arguments(cls, parser):
        I2CAnalyzer.add_arguments(parser)
        parser.add_argument(
            'bits',
            help=(
                'Number of bits of precision this ADC provides; for the '
                'AD7991 you should enter 12, the AD7995: 10, and the '
                'AD7999: 8.'
            ),
            type=int,
        )
        parser.add_argument(
            '--reference-voltage',
            help=(
                'The reference voltage in use by the ADC.  Used for '
                'displaying actual voltages as well as returned ADC '
                'values.  Note that this does not take into account '
                'the state of the REF_SEL configuration setting; '
            ),
            type=float,
            default=None
        )

    def get_configuration_settings(self, value):
        """ Returns channels and features enabled in a configuration.

        Uses WRITE frame #1 (zero-indexed)
        """
        ch3 = value & (1 << 7)
        ch2 = value & (1 << 6)
        ch1 = value & (1 << 5)
        ch0 = value & (1 << 4)

        channels = {
            '0': ch0,
            '1': ch1,
            '2': ch2,
            '3': ch3,
        }
        channels_enabled = [
            name for name, en in channels.items() if en
        ]

        ref_sel = value & (1 << 3)
        fltr = value & (1 << 2)
        bit_trial = value & (1 << 1)
        sample = value & (1 << 0)

        features = {
            ('External Reference', 'Ext Ref'): ref_sel,
            ('SDA and SCL Filtering', 'Filter'): not fltr,
            ('Bit Trial Delay', 'Bit Trial'): not bit_trial,
            ('Sample Delay', 'Samp. Del.'): not sample,
        }
        features_enabled = [
            names for names, en in features.items() if en
        ]

        return channels_enabled, features_enabled

    def get_adc_channel(self, frame1) -> int:
        """ Returns the ADC channel in use for a returned measurement.

        Uses READ frame #1 (zero-indexed)
        """
        return (frame1 >> 4) & 0b11

    def get_adc_value(self, frame1, frame2) -> int:
        """ Returns the ADC value for a measurement.

        Uses READ frames #1 and #2 (zero-indexed)
        """
        # The AD799x series left-justifies their ADC results,
        # so the second frame's rightmost bits may be empty
        # on devices with lesser capabilities.  The below two
        # shifts shift the contents of the first frame to the
        # left and the second to the right such that when added together
        # the rightmost bit provided by the ADC (in the second frame) is
        # in the 1s position, and the rightmost bit of the first frame
        # is one bit to the left of the leftmost bit of the second.
        frame_one_left_shift = self._bits - 4
        frame_two_right_shift = 0 - (self._bits - 12)

        msb = ((frame1 & 0b1111) << frame_one_left_shift)
        lsb = frame2 >> frame_two_right_shift

        return msb + lsb

    def get_adc_voltage(self, value):
        if not self._reference_voltage:
            return None

        return (value / (2**self._bits)) * self._reference_voltage

    def get_displayable_adc_value(self, value):
        if not self._reference_voltage:
            return [str(value)]

        voltage = (value / (2**self._bits)) * self._reference_voltage

        return [
            "{voltage:.4f} V ({raw})".format(
                voltage=voltage,
                raw=value,
            ),
            "{voltage:.4f} V".format(
                voltage=voltage,
                raw=value,
            ),
            "{voltage:.2f}".format(
                voltage=voltage,
                raw=value,
            )
        ]

    def handle_bubble(
        self,
        packet_id: Optional[int],
        frame_index: int,
        start_sample: int,
        end_sample: int,
        frame_type: int,
        flags: int,
        direction: Channel,
        value: int
    ) -> List[str]:
        if not self.packet_address_matches(packet_id):
            return []

        address_frame = self.get_packet_nth_frame(packet_id, 0)
        is_read = address_frame['value'] & 0b1
        is_write = not is_read
        if (
            (
                not self.get_packet_length(packet_id) == 2
                and is_write
            )
            or
            (
                not self.get_packet_length(packet_id) == 3
                and is_read
            )
        ):
            # We don't have quite enough data to do anything
            return []

        frame_index = self.get_packet_frame_index(packet_id, frame_index)

        if is_write:
            if frame_index == 0:
                return [
                    "Write to ADC Configuration",
                    "W to ADC",
                    "W",
                ]
            elif frame_index == 1:
                ch_enabled, feat_enabled = self.get_configuration_settings(
                    value
                )

                return [
                    (
                        'Channels: {channels}; Features: {features}'.format(
                            channels=', '.join(ch_enabled),
                            features=', '.join(f[0] for f in feat_enabled),
                        )
                    ),
                    (
                        'Ch: {channels}; Feat: {features}'.format(
                            channels='/'.join(ch_enabled),
                            features='/'.join(f[1] for f in feat_enabled),
                        )
                    ),
                    (
                        'Ch: {channels}; Feat: {features}'.format(
                            channels='/'.join(ch_enabled),
                            features=bin(value & 0b1111)
                        )
                    ),
                    (
                        'Ch: {channels}'.format(
                            channels='/'.join(ch_enabled),
                        )
                    ),
                    (
                        '{channels}'.format(
                            channels='/'.join(ch_enabled),
                        )
                    ),
                    bin(value)
                ]
        else:
            if frame_index == 0:
                return [
                    "Read ADC Value",
                    "R from ADC",
                    "R",
                ]
            elif frame_index == 1:
                channel = self.get_adc_channel(value)

                return [
                    "Channel: {ch}".format(ch=channel),
                    "Ch: {ch}".format(ch=channel),
                    channel,
                ]
            elif frame_index == 2:
                frame_one = self.get_packet_nth_frame(packet_id, 1)

                adc_result = self.get_adc_value(frame_one['value'], value)

                return self.get_displayable_adc_value(adc_result)
        return [
            bin(value)
        ]

    def handle_tabular(
        self,
        packet_id: Optional[int],
        frame_index: int,
        start_sample: int,
        end_sample: int,
        frame_type: int,
        flags: int,
        sda: int,
        value2: int,
    ) -> List[str]:
        no_result = [' ']  # Saleae requires that we return _something_

        if not self.packet_address_matches(packet_id):
            return no_result

        address_frame = self.get_packet_nth_frame(packet_id, 0)
        is_read = address_frame['value'] & 0b1
        is_write = not is_read
        if (
            (
                not self.get_packet_length(packet_id) == 2
                and is_write
            )
            or
            (
                not self.get_packet_length(packet_id) == 3
                and is_read
            )
        ):
            # We don't have quite enough data to do anything
            return no_result

        if self.get_packet_frame_index(packet_id, frame_index) != 1:
            return no_result

        if is_write:
            configuration_frame = self.get_packet_nth_frame(packet_id, 1)
            ch_enabled, feat_enabled = self.get_configuration_settings(
                configuration_frame['value']
            )

            return [
                '[ADC config] Channels enabled: {chan}; '
                'Features enabled: {feat}'.format(
                    chan=', '.join(ch_enabled),
                    feat=', '.join(f[0] for f in feat_enabled)
                )
            ]
        elif is_read:
            frame_one = self.get_packet_nth_frame(packet_id, 1)
            frame_two = self.get_packet_nth_frame(packet_id, 2)

            channel = self.get_adc_channel(frame_one['value'])
            adc_result = self.get_adc_value(
                frame_one['value'],
                frame_two['value'],
            )

            return [
                '[ADC read] channel {chan}: {value}'.format(
                    chan=channel,
                    value=self.get_displayable_adc_value(
                        adc_result
                    )[0]
                )
            ]

        return no_result


if __name__ == '__main__':
    AD7995Analyzer.run(sys.argv[1:])
