#!/usr/bin/env python
# Copyright 2016, DELLEMC, Inc.

"""
The script generate a new manifest for a new branch according to another manifest

usage:
./on-tools/manifest-build-tools/HWIMO-BUILD on-tools/manifest-build-tools/application/generate_manifest.py \
--branch master \
--date "$date" \
--timezone "+0800" \
--builddir b \
--force \
--git-credential https://github.com,GITHUB \
--jobs 8

The required parameters: 
branch: The branch name of each repository in manifest file.
date: The commit of each repository are last commit before the date.
      The valid date: current (the commit of each repository are the lastest commit")
                      yesterday (the commit of each repository are the last commit of yesterday")
                      date string, such as: 2016-12-01 00:00:00 (the commit of each repository are the last commit before the date")

timezone: The Time Zone for the date, such as: +0800, -0800, -0500
git-credential: Git credentials for CI services.
builddir: The directory for checked repositories.

The optional parameters:
force: If true, overwrite the destination manifest file even it already exists.
jobs: number of parallel jobs to run. The number is related to the compute architecture, multi-core processors...
"""
import os
import sys
import argparse
from dateutil.parser import parse
from datetime import datetime,timedelta

try:
    import common
    from ManifestGenerator import *
except ImportError as import_err:
    print import_err
    sys.exit(1)

def parse_command_line(args):
    """
    Parse script arguments.
    :return: Parsed args for assignment
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch",
                        required=True,
                        help="The branch of repositories in new manifest",
                        action="store")

    parser.add_argument("--date",
                         default="current",
                         required=True,
                         help="Generate a new manifest with commit before the date, such as: current, yesterday, 2016-12-13 00:00:00",
                         action="store")

    parser.add_argument("--timezone",
                         default="+0800",
                         required=True,
                         help="The time zone for parameter date",
                         action="store")

    parser.add_argument("--builddir",
                        required=True,
                        help="destination for checked out repositories",
                        action="store")

    parser.add_argument("--git-credential",
                        required=True,
                        help="Git credential for CI services",
                        action="append")

    parser.add_argument("--force",
                        help="use destination manifest file, even if it exists",
                        action="store_true")
    parser.add_argument("--jobs",
                        default=1,
                        help="Number of parallel jobs to run",
                        type=int)

    parsed_args = parser.parse_args(args)
    return parsed_args

def convert_date(date_str):
    try:
        if date_str == "yesterday":
            utc_now = datetime.utcnow()
            utc_yesterday = utc_now + timedelta(days=-1)
            date = utc_yesterday.strftime('%Y%m%d 23:59:59')
            dt = parse(date)
            return dt
        else:
            dt = parse(date_str)
            return dt
    except Exception, e:
        raise ValueError(e)

def main():
    try:
        # parse arguments
        args = parse_command_line(sys.argv[1:])
        
        if args.date == "current":
            utc_now = datetime.utcnow()
            date_str = utc_now.strftime("%Y%m%d")
            dest_manifest = "{branch}-{date}".format(branch=args.branch, date=date_str)
            generator = ManifestGenerator(dest_manifest, args.branch, args.builddir, args.git_credential, jobs=args.jobs, force=args.force)
        else:
            dt = convert_date(args.date)
            date_str = dt.strftime("%Y%m%d")
            dest_manifest = "{branch}-{date}".format(branch=args.branch, date=date_str)
            date_str = "{0} {1}".format(dt.strftime("%Y-%m-%d %H:%M:%S"), args.timezone)
            generator = SpecifyDayManifestGenerator(dest_manifest, args.branch, date_str, args.builddir, args.git_credential, jobs=args.jobs, force=args.force)
            
        generator.update_manifest()
        generator.generate_manifest()
    except Exception, e:
        print "Failed to generate new manifest for {0} due to \n{1}\nExiting now".format(args.branch, e)
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)
