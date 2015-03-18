# node-foreman
node-foreman is a tool for starting multiple processes with one command and
combining their stdout together into the stdout of the foreman process.

The procfiles and .env file in this directory are used by node-foreman, and can be
configured to start multiple services with one command. The aim is to make development
tasks easier and faster, e.g. stopping all services, pulling from git, and restarting
all services becomes 10 commands shorter using foreman.

## Installation

```
cd on-tools
npm install

Add on-tools/node_modules/.bin to your PATH variable in .bashrc (linux)
or .bash_profile (osx)
```

## Usage

Edit the .env file, changing BASEPATH to equal whatever directory your
renasar repos are held in.

There are several pre-defined procfiles with different configurations for
running renasar processes.

To run all renasar services at once, cd to this directory and run:

```
sudo nf start
```

To run only taskgraph and http:

```
sudo nf -j major-services-procfile start
```

To run only dhcp, tftp and syslog:

```
sudo nf -j minor-services-procfile start
```

To run any individual process from this directory, choose any of the individual
service procfiles (dhcp-procfile, http-procfile, etc.) and run:

```
sudo nf -j <procfile> start
```

Obviously this last command can simply be performed by changing directories
into on-<repo> and running sudo node index.js, but the intent here is to
enable developers to invoke all Renasar services from one directory. As always,
bash aliases can be created to shorten these commands. The downside of this
approach is the loss of natural log coloring from the processes themselves. Buyer beware.

FYI: node-foreman will kill all processes on exit of any one process.
