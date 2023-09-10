import argparse
import sys
from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.log import init_console_logging
from tp.handler import D5gTransactionHandler
# TODO add config class/files when necessary

# Transaction Processor (tp) for the "d5g" family of Sawtooth transactions.

DISTRIBUTION_NAME = 'sawtooth-d5g-orchestrator'

def parse_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-c', '--connect',
        help='Validator connection')
    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='more detailed output')
    return parser.parse_args(args)

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    opts = parse_args(args)
    processor = None
    if opts.connect is None:
        opts.connect =  "tcp://127.0.0.1:4004" # default
    try:
        # TODO fix opts.connect to actually pull correctly
        processor = TransactionProcessor(url=opts.connect)
        # todo maybe add log_config from xo example (from sawtooth_sdk.processor.log import log_configuration)
        init_console_logging() #verbose_level=opts.verbose)
        handler = D5gTransactionHandler()
        processor.add_handler(handler)
        print("d5g tp starting...")
        processor.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error: {e}")
        raise e
    finally:
        if processor is not None:
            processor.stop()
    print("d5g tp exiting...")

if __name__ == "__main__":
    main()
