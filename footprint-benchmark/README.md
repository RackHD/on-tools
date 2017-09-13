# Footprint Benchmark Overview

Footprint benchmark collects system data and draw diagrams to compare with previous runs.
Details can be found in WIKI page:
[proposal-footprint-benchmarks](https://github.com/RackHD/RackHD/wiki/proposal-footprint-benchmarks)
The benchmark data collection process can start/stop independently and users can get the footprint info about any
operation they carry out during this period of time.

## Precondition

The machine running RackHD can use apt-get to install packages, which means it must have accessible sources.list

## Setup

NOTE: virtualenv version used 1.11.4 (Ubuntu). Using virtualenv is optional here but suggested.

    virtualenv .venv
    source .venv/bin/activate
    sudo pip install -r requirements.txt

## Settings

Following parameters are required at the first time user issuing the test, and stored in .ansible_config

    localhost username and password: information of the machine running the data collection
    rackhd ip, ssh port, username and password: information of the machine running rackhd

## Running the benchmark data collection

Start|Stop benchmark data collection

    python benchmark.py --start|stop

Get the directory of the latest log data

    python benchmark.py --getdir

## Getting the result

Footprint report is in ~/benchmark/(timestamp)/(case)/report of the test machine.
Report in html format can display its full function by the following command to open the browser
and drag the summary.html to it.

    chrome.exe --user-data-dir="C:/Chrome dev session" --allow-file-access-from-files

Data summary and graph is shown by process and footprint matrix. Data collected in previous runs
can be selected to compare with the current one.
