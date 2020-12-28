#!/usr/bin/env python
import vobject
import glob
import csv
import argparse
import os.path
import sys
import logging
import collections

column_order = [
    'Name',
    'Full name',
    'Cell phone',
    'Work phone',
    'Home phone',
    'Email',
    'Note',
]

def get_phone_numbers(vCard):
    # order determines priority; earlier-declarations take precendence
    nums = {"CELL": None, "HOME": None, "WORK": None, "MAIN": None, "pref": None, "PAGER": None, "FAX": None, "OTEHR": None, "VOICE": None}
    
    for tel in vCard.tel_list:
        if vCard.version.value == '2.1':
            for k in nums:
                if k in tel.singletonparams:
                    nums[k] = str(tel.value).strip()
                    break
            else:
                logging.warning("Warning: Unrecognized phone number category in `{}'".format(vCard))
                tel.prettyPrint()
        elif vCard.version.value == '3.0':
            if 'TYPE' in tel.params:
                for k in nums:
                    if k in tel.params['TYPE']:
                        nums[k] = str(tel.value).strip()
                        break
                else:
                    logging.warning(f"Unrecognized phone number category {tel.params['TYPE']} in `{vCard}'")
                    tel.prettyPrint()
            else:
                logging.debug("No phone numbers in `{}'".format(vCard))
        else:
            raise NotImplementedError("Version not implemented: {}".format(vCard.version.value))
    return nums["CELL"], nums["HOME"], nums["WORK"]

def get_info_list(vcard_filepath):
    vcards = []
    with open(vcard_filepath) as fp:
        vCards = vobject.readComponents(fp.read())
    for vCard in vCards:
        vCard.validate()
        vcard = collections.OrderedDict()
        for column in column_order:
            vcard[column] = None
        name = cell = work = home = email = note = None
        for key, val in list(vCard.contents.items()):
            if key == 'fn':
                vcard['Full name'] = vCard.fn.value
            elif key == 'n':
                name = str(vCard.n.valueRepr()).replace('  ', ' ').strip()
                vcard['Name'] = name
            elif key == 'tel':
                cell, home, work = get_phone_numbers(vCard)
                vcard['Cell phone'] = cell
                vcard['Home phone'] = home
                vcard['Work phone'] = work
            elif key == 'email':
                email = str(vCard.email.value).strip()
                vcard['Email'] = email
            elif key == 'note':
                note = str(vCard.note.value)
                vcard['Note'] = note
            else:
                # An unused key, like `adr`, `title`, `url`, etc.
                pass
        if name is None:
            logging.warning("no name for file `{}'".format(vcard_filepath))
        if all(telephone_number is None for telephone_number in [cell, work, home]):
            logging.debug("no telephone numbers for file `{}' with name `{}'".format(vcard_filepath, name))
        vcards.append(vcard)

    return vcards

def readable_directory(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(
            'not an existing directory: {}'.format(path))
    if not os.access(path, os.R_OK):
        raise argparse.ArgumentTypeError(
            'not a readable directory: {}'.format(path))
    return path

def writable_file(path):
    if os.path.exists(path):
        if not os.access(path, os.W_OK):
            raise argparse.ArgumentTypeError(
                'not a writable file: {}'.format(path))
    else:
        # If the file doesn't already exist,
        # the most direct way to tell if it's writable
        # is to try writing to it.
        with open(path, 'w') as fp:
            pass
    return path

def main():
    parser = argparse.ArgumentParser(
        description='Convert a bunch of vCard (.vcf) files to a single TSV file.'
    )
    parser.add_argument(
        'read_dir',
        type=readable_directory,
        help='Directory to read vCard files from.'
    )
    parser.add_argument(
        'tsv_file',
        type=writable_file,
        help='Output file',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='More verbose logging',
        dest="loglevel",
        default=logging.WARNING,
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        '-d',
        '--debug',
        help='Enable debugging logs',
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    vcard_pattern = os.path.join(args.read_dir, "*.vcf")
    vcards = sorted(glob.glob(vcard_pattern))
    if len(vcards) == 0:
        logging.error("no files ending with `.vcf` in directory `{}'".format(args.read_dir))
        sys.exit(2)

    # Tab separated values are less annoying than comma-separated values.
    with open(args.tsv_file, 'w') as tsv_fp:
        writer = csv.writer(tsv_fp, delimiter='\t')
        writer.writerow(column_order)

        for vcard_path in vcards:
            for vcard_info in get_info_list(vcard_path):
                writer.writerow(list(vcard_info.values()))

if __name__ == "__main__":
    main()
