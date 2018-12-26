# Python Tools for Enrichable Saleae Analyzers

The built-in analyzers for the Saleae Logic provides you with only a few basic options for how to display the transferred bytes -- as ascii text, or in one of several numeric formats.
What if you're working with an device that encodes more than just integer or text data into those bytes, or even stores multiple values in each byte that will require you to either do the math in your head, export the data for post-processing, or display the frame as binary bits so you can directly look at the parts that matter to you?
That's the sort of thing computers are great at doing; why don't we just let your computer do that?

This Python library -- in tandem with special "Enrichable" versions of Saleae Logic analyzers -- makes it easy for you to enrich the data displayed so you can provide your own text and markers to display for each frame.
Now you can focus on solving your actual problem instead of interpreting inscrutible hex values.

## Related

* [saleae-enrichable-spi-analyzer](https://github.com/coddingtonbear/saleae-enrichable-spi-analyzer): A version of the Saleae SPI analyzer that supports enrichment.
* [saleae-enrichable-i2c-analyzer](https://github.com/coddingtonbear/saleae-enrichable-i2c-analyzer): A version of the Saleae I2C analyzer that supports enrichment.

## Installation

*Note*: This requires Python 3.4!

If you want to use the latest release; just install directly from pypi:

```
pip install saleae_enrichable_analyzer
```

To use the development version, just clone this repository and run:

```
pip install .
```

## Use

Using this is as simple as creating your own module somewhere that subclasses `saleae_enrichable_analyzer.EnrichableAnalyzer` with methods for the features you'd like to use;
here is a basic example:

```python
import sys
from typing import List, Optional

from saleae_enrichable_analyzer import (
    Channel, EnrichableAnalyzer, Marker, MarkerType
)


class MySimpleAnalyzer(EnrichableAnalyzer):
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
        return [
            "This message will be displayed above every frame in the blue bubble"
        ]

    def handle_marker(
        self,
        packet_id: Optional[int],
        frame_index: int,
        sample_count: int,
        start_sample: int,
        end_sample: int,
        frame_type: int,
        flags: int,
        mosi_value: int,
        miso_value: int
    ) -> List[Marker]:
        markers = []

        if(miso_value == 0xff) {
            # This will show a "Stop" marker on the zeroth sample
            # of the frame on the MISO channel when its value is 0xff.
            markers.append(
                Marker(0, Channel.MISO, MarkerType.Stop)
            )
        }

        return markers

if __name__ == '__main__':
    MySimpleAnalyzer.run(sys.argv[1:])
```

The methods described below can be implemented for interacting with Saleae Logic.
Methods not implemented will automatically be disabled according to the
"Feature (Enablement)" section above.

See the following examples for concrete implementations:

* [simple_SC16IS7xx.py](
https://github.com/coddingtonbear/saleae-enrichable-spi-analyzer/blob/master/examples/simple_SC16IS7xx.py): Implements a simple enricher for displaying register, channel, and data for the SC16IS7xx series of SPI UARTs.
* [simple_ad7995.py](https://github.com/coddingtonbear/saleae-enrichable-i2c-analyzer/blob/master/examples/simple_ad7995.py): Implements a slightly-more completed enricher for displaying detailed configuration and read data for the AD7995 I2C ADC.

### `handle_bubble`

```python
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
        return []
```

Set the bubble text (the text shown in blue abov the frame) for this frame.
By default, no bubble is shown.  It is recommended that you return multiple
strings of varying lengths.

### `handle_marker`

```python
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
    ) -> List[Marker]:
        return []
```

Return markers to display at given sample points.
By default, no markers are displayed.

This method can be implemented for reasons other than wanting to display
markers, too --
it is useful if your script needs to receive all frames of data in the order they were received.  In such cases, you can record your packets in the body of the method, and return an empty list.  See [simple_ad7995.py](https://github.com/coddingtonbear/saleae-enrichable-i2c-analyzer/blob/master/examples/simple_ad7995.py) for a concrete example of that strategy in use.

### `handle_tabular`

```python
    def handle_tabular(
        self,
        packet_id: Optional[int],
        frame_index: int,
        start_sample: int,
        end_sample: int,
        frame_type: int,
        flags: int,
        value1: int,   # SPI: MOSI; I2C: SDA
        value2: int,   # SPI: MISO; I2C: Undefined
    ) -> List[str]:
        return []
```

Data to display in the tabular "Decoded Protocols" section.
