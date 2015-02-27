#!/bin/bash

sudo ifconfig bridge0 10.1.1.1/24 up
sudo ifconfig bridge0 addm en0
