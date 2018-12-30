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

*Note*: This requires Python 3.5!

If you want to use the latest release; just install directly from pypi:

```
pip install saleae_enrichable_analyzer
```

To use the development version, just clone this repository and run:

```
pip install .
```

## Bundled enrichment scripts

This library is bundled with a handful of enrichment scripts out-of-the-box;
you can use any of these by following the instructions below.
Note that you may need to replace `python` in the examples with the path to the relevant Python binary --
if you installed this library into a virtual environment, that path should point to that environment's `python`, of course.

### SPI

#### SC16IS75xx

Supports the SC16IS75xx series of SPI UART chips.

Known supported:

* SC16IS740
* SC16IS750
* SC16IS752
* SC16IS760
* SC16IS762

Usable by using the following enrichment script:

```
python -m saleae_enrichable_analyzer.scripts.spi.SC16IS75xx
```

### I2C

#### AD799x

Supports the AD799x series of I2C ADC chips.

Known supported:

* AD7991 (12 bit)
* AD7995 (10 bit)
* AD7999 (8 bit)

Usable by using the following enrichment script; be sure to replace
`BITS` with the number of bits your ADC provides, and `ADDRESS` with
your device's base-2 I2C address:

```
python -m saleae_enrichable_analyzer.scripts.i2c.AD799x ADDRESS BITS
```

Additionally, you can provide the `--reference-voltage=VOLTAGE` argument
to display the calculated voltage as well as the raw ADC value.

## Writing your own Enrichment Script

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

If you'd like to see simple concrete examples,
you can refer to the following:

* [simple_SC16IS7xx.py](
https://github.com/coddingtonbear/saleae-enrichable-spi-analyzer/blob/master/examples/simple_SC16IS7xx.py): Implements a simple enricher for displaying register, channel, and data for the SC16IS7xx series of SPI UARTs.
* [simple_ad7995.py](https://github.com/coddingtonbear/saleae-enrichable-i2c-analyzer/blob/master/examples/simple_ad7995.py): Implements a slightly-more completed enricher for displaying detailed configuration and read data for the AD7995 I2C ADC.

But also be aware that the `scripts` directory contains examples, too,
but they may be somewhat more advanced in functionality.

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
it is useful if your script needs to receive all frames of data in the order they were received.
In such cases, you can record your packets in the body of the method,
and return an empty list.
See the [base I2CAnalyzer class](https://github.com/coddingtonbear/python-saleae-enrichable-analyzer/blob/f617c9fb22c68f06a863dd0197c57e17f085a789/saleae_enrichable_analyzer/scripts/i2c/base.py#L66) for a concrete example of that strategy in use.

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
Due to limitations within Saleae logic: if implemented, this method must return exactly the same number of strings in the result array for each request;
if you attempt to do otherwise, you may see the following error (sic) "Error: Number of strings in the analyzer results are diffrenet for different display bases" followed by a SIGSEGV.

## Debugging your enrichment script

If Saleae Logic crashes when using your enrichment script,
it's almost certainly the fault of your script and not Saleae Logic.
Luckily, debugging is quite easy by using the built-in logging features.

By default, logging is written to stderr,
but given that most of us do not run Saleae Logic in a terminal, that output isn't immediately visible.
To see that logging output without running in a terminal,
you can use the following two flags:

* `--loglevel=LEVEL`: Set the level of reported output.
  When debugging, you likely want to use `--loglevel=DEBUG`.
  Valid options (in order of increasing verbosity) include
  `CRITICAL`, `ERROR`, `WARNING`, `INFO`, and `DEBUG`.
  The output displayed for a selected level includes the output of all
  lower-verbosity levels.
* `--logpath=PATH`: Set a file path to write your logging output to.

Note that these flags must follow the module name when using a bundled enrichment script.
For example, to debug the bundled AD799x enrichment script (which itself requires two positional arguments),
you can set the following for your "Enrichment Script" in Saleae Logic:

```
python -m saleae_enrichable_analyzer.scripts.i2c.AD799x --loglevel=DEBUG --logpath=/tmp/logic_debug.log 12 0101000
```

If you're debugging a script you've written, though,
simply provide the flags following your script path:

```
python /path/to/your/enrichment/script.py --loglevel=DEBUG --logpath=/tmp/logic_debug.log
```

Logging messages will continue to be written to stderr regardless of whether you've enabled logging to a file,
and if you find that the logging output written by your script is not revealing,
it may be helpful to run Saleae Logic in a terminal to see both the logging output of Saleae Logic and your script interleaved.
