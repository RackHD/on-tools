# setup_iso.py [http://path.to/file.iso | /path/to/file.iso] [/var/destination]
#
# Deploy the ISO file contents to the specified destination directory such that
# destination directory can be used as a target for RackHD OS bootstrap workflows
import argparse
import subprocess
import os
import errno
import os.path
import tempfile
import atexit
import sys
import shutil
import re
import urllib
import time

tmpdir = ''
verbose=1

# Cleanup
@atexit.register
def cleanup_tmp():
    if tmpdir != '':
        subprocess.check_call(['umount', '-l', tmpdir])
        os.rmdir(tmpdir)

def get_iso_info(fname):
    # Access ISO to determine OS type from supported list
    label1=subprocess.Popen(['isoinfo', '-i', fname, '-d'], stdout=subprocess.PIPE)
    return label1.stdout.read()

def get_setup_exe_name_version(srcdir):
    # To get the name and version from setup.exe
    os.chdir(srcdir)
    label1=subprocess.Popen(['strings', '-e', 'l', 'setup.exe'], stdout=subprocess.PIPE)
    setup_info =  label1.stdout.read().split('\n')
    osname_id = setup_info.index(' Operating System') # The os name is next to 'Operating System' on the left
    osname = setup_info[osname_id - 1].strip(' ')

    pver_id = setup_info.index('ProductVersion')
    pver = setup_info[pver_id + 1].strip(' ') # The OS version is next to 'ProductVersion' on the right
    win2012_pver_pattern = '^6\.(.+)'
    win2016_pver_pattern = '^10\.(.+)'
    if re.search(win2012_pver_pattern, pver):
        osver = 'Windows2012'
    elif re.search(win2016_pver_pattern, pver):
        osver = 'Windows2016'
    return osname, osver

def do_setup_repo(osname, osver, src, dest, link):
    print 'Installing {0} {1} to {2}/{0}/{1}'.format(osname, osver, dest)
    print 'symbolic link base directory {0}'.format(link)
    dstpath=dest + '/' + osname + '/' + osver
    if os.path.isdir(dstpath):
        print 'Found existing directory, bailing...'
        sys.exit(1)

    if osname is 'LiveCD':
        initrd='initrd.img'
        vmlinuz='vmlinuz'
        if os.path.isfile(src+'/isolinux/initrd0.img'):
            initrd='initrd0.img'
            vmlinuz='vmlinuz0'
        mount1 = subprocess.Popen(['mount'], stdout=subprocess.PIPE)
        mount2 = subprocess.Popen(['grep', src], stdin=mount1.stdout, stdout=subprocess.PIPE)
        mount3 = subprocess.Popen(['awk', '{print $1}'], stdin=mount2.stdout, stdout=subprocess.PIPE)
        isoname = mount3.communicate()[0]

        iso_basename = os.path.basename(isoname).strip()
        iso_dirname = os.path.dirname(isoname).strip()

        os.makedirs(dstpath)

        syscall = '(cd "'+iso_dirname+'" && echo "'+iso_basename+'" | cpio -H newc --quiet -L -o )'
        syscall += ' | gzip -9'
        syscall += ' | cat '+src+'/isolinux/'+initrd+' - > '+dstpath+'/initrd.img'
        os.system(syscall)

        shutil.copyfile(src+'/isolinux/'+vmlinuz, dstpath+'/'+vmlinuz)
    elif osname == 'Ubuntu':
        # Execute 'ls -l' and find out the soft link that points to itself
        p = subprocess.Popen(['ls', '-l', src], stdout=subprocess.PIPE)
        files = p.stdout.read().split('\n')
        ignoreList = list()
        # The first element is something like "Total 212" and the last element is '', so skip both while finding the softlink
        # The for loop is to find 'ubuntu' from  a list like   ["lr-xr-xr-x","root","root","ubuntu","->","."]
        for f in files[1:-1]:
            f_info = f.split(' ')
            if 'l'  in f_info[0] and f_info[-2] == '->' and f_info[-1] == '.':
                ignoreList.append(f_info[-3])

        shutil.copytree(src, dstpath, ignore=shutil.ignore_patterns(*ignoreList))
    else:
        shutil.copytree(src, dstpath)

    os.system('ln -sf ' + dest + "/" + osname + ' ' + link + '/on-http/static/http/')
    os.system('ln -sf ' + dest + "/" + osname + ' ' + link + '/on-tftp/static/tftp/')

def mount_iso(fname):
    # Mount the ISO to tmp directory
    tmpdir=tempfile.mkdtemp()
    if os.path.isdir(tmpdir) and os.access(tmpdir, os.W_OK):
        try:
            subprocess.check_call(['mount', '-o', 'loop', fname, tmpdir])
        except subprocess.CalledProcessError as e:
            print 'Failed with error code: {0}'.format(e.returncode)
            os.rmdir(tmpdir)
            return ''
    else:
        print 'Unable to access ISO image'
        os.rmdir(tmpdir)
        return ''

    return tmpdir

def determine_os_ver(srcdir, iso_info):
    osname = ''
    osver = ''
    vid = ''
    m = re.search('^Volume id\:\s+(.+)$', iso_info, re.MULTILINE)
    if m:
        vid = m.group(1)

    if 'Application id: ESXIMAGE' in iso_info:
        osname='ESXi'
        if 'ESXI-6.0.0' in vid:
            osver='6.0'
        elif 'ESXI-5.5' in vid:
            osver='5.5'
    else:
        src_dir_list=os.listdir(srcdir)
        if "RPM-GPG-KEY-redhat-release" in src_dir_list:
            osname = 'RHEL'
            osver = '7.0'
        elif "RPM-GPG-KEY-CentOS-Testing-7" in src_dir_list:
            osname = "Centos"
            osver = '7.0'
        elif 'ubuntu' in src_dir_list:
            # For ubuntu, the osver is combined by the version name(add -server for unbuntu server and without -server
            # for desktop) and version number, e.g.ubuntu-server-16.04
            osname='Ubuntu'
            if vid == '': assert ValueError, "The volume ID is not get correctly"
            ver_pattern = '(\w+\-?\w+)\s+(\d+\.?\d+\.?\d+?)'
            m = re.search(ver_pattern, vid)
            assert m.group(1), "The version name(e.g., unbuntu-server) for ubuntu is not correct"
            assert m.group(2), "The version for ubuntu is not correct"
            osver = m.group(1) + '-' + m.group(2)
        elif 'isolinux' in src_dir_list:
            print 'attempting LiveCD netboot'
            osname = 'LiveCD'
            osver = vid

        elif 'suse' in src_dir_list:
            osname='SUSE'
            if vid == '': assert ValueError, "The volume ID is not get correctly"
            ver_pattern = '(.+)-DVD-(.+)'
            m = re.search(ver_pattern, vid)
            assert m.group(1), "The version name is not retrieved correctly"
            osver = m.group(1)
        elif 'setup.exe' in src_dir_list:
            osname, osver = get_setup_exe_name_version(srcdir)
        else:
             for i in src_dir_list:
                 if "PHOTON" in i:
                     osname="PHOTON"
                     if vid == '': assert ValueError, "The volume ID is not get correctly"
                     osver = vid.lstrip('PHOTON_')


    return osname, osver

def show_progress(a,b,file_size):
    if verbose:
        file_size_dl = a * b
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

parser = argparse.ArgumentParser(description='Setup the OS repo from an ISO image')
parser.add_argument('iso', metavar='N', help='the ISO image or URL to ISO image')
parser.add_argument('dest', metavar='N', help='the destination directory to setup')
parser.add_argument('--link', metavar='N', help='the symbolic link path', default='/var/renasar')
args = parser.parse_args()


# Ensure the image exists and is readable
fname = ''
if os.path.isfile(args.iso) and os.access(args.iso, os.R_OK):
    fname = args.iso
else:
    (filename,headers) = urllib.urlretrieve(url=args.iso,reporthook=show_progress)
    print '\n'
    fname = filename

tmpdir = mount_iso(fname)
if not tmpdir:
    print 'Failed to mount ISO image'
    sys.exit(1)

info = get_iso_info(fname)
if not info:
    print 'Failed to get iso info'
    sys.exit(1)

osname,osver = determine_os_ver(tmpdir, info)
if not osname or not osver:
    print 'Failed to get os name and/or os version information'
    sys.exit(1)

do_setup_repo(osname, osver, tmpdir, args.dest, args.link)

