''' Helper commmands to manage CSV files '''

# Lazy load pandas to increase startup speed
# pylint: disable=import-outside-toplevel

from .helper import fatal_error

def set_up_merge_csv(subparsers):
    ''' Set up arguments for the `merge-csv` command '''

    parser = subparsers.add_parser('merge-csv',
            help="Allows to combine two CSV files into a new CSV file")

    parser.add_argument('infile1', type=str)
    parser.add_argument('infile2', type=str)
    parser.add_argument('outfile', type=str)

    parser.set_defaults(func=_merge_csv_cmd)

def _merge_csv_cmd(args):
    from pandas import read_csv, concat

    def _extract_constants(path) -> str:
        with open(path, 'r', encoding='utf-8') as infile:
            for line in infile.readlines():
                if line.startswith('# constants:'):
                    return line
        fatal_error(f"No constants found in file {path}")

    consts1 = _extract_constants(args.infile1)
    consts2 = _extract_constants(args.infile2)

    if consts1 != consts2:
        fatal_error("Cannot merge CSV files: Constants do not match!")

    df1 = read_csv(args.infile1, comment='#', skipinitialspace=True)
    df2 = read_csv(args.infile2, comment='#', skipinitialspace=True)

    merged = concat([df1, df2])

    with open(args.outfile, 'w', encoding='utf-8') as outfile:
        outfile.write(consts1)
        merged.to_csv(outfile, index=False)
