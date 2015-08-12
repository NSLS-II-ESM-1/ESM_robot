from contextlib import contextmanager
import os
import glob

import ophyd.controls.areadetector.detectors as ad
import ophyd.controls.positioner as ocp

import numpy as np

# define the motors
rot = ocp.EpicsMotor('XF:21IDC-ES{SH:proto-Ax:R}Mtr.VAL', 
                     name='rot')

claw = ocp.EpicsMotor('XF:21IDC-ES{SH:proto-Ax:C}Mtr', 
                      name='claw')
manip = ocp.EpicsMotor('XF:21IDC-ES{SH:proto-Ax:T}Mtr', 
                       name='manip')

feed = ocp.EpicsMotor('XF:21IDC-ES{SH:proto-Ax:F}Mtr', 
                      name='feed')

# camera
cam = ad.ProsilicaDetector('ESM:')


@contextmanager
def rolling_record_motion(fp, run_number, buffer_number=10):
    """
    This context manager is for collecting a series of movies
    in a rolling buffer.  This assumes that the current path that
    the file plugin has in '/true/base/path/NN'.  The files will be
    saved into '/true/base/path/(run_number % buffer_number)'.

    Any files in the output folder which match the file template glob
    will be deleted prior to capturing any new data.


    Parameters
    ----------
    fp : FilePlugin
        The file plugin of the camera to use.  Must have tiff file
        support.  It is assumed that all of the exposure details,
        basepath, template, ect have been set before hand.

    run_number : int
        The run number, used to compute where to save the files

    buffer_number : int, optional
        The number of past movies to keep
       
    """
    
    base_path = os.path.dirname(fp.file_path.value.rstrip('/'))

    new_path = os.path.join(base_path, 
                            '{:02d}'.format(run_number % buffer_number))
    os.makedirs(new_path, exist_ok=True)
    fp.file_path.value = new_path
    
    # this assumes that the fname pattern is more-or-less
    # %s%s_%d.ext % (path, name, number)

    exist_glob = os.path.join(new_path, fp.file_name.value) + '*'

    # remove any existing files
    for f in glob.iglob(exist_glob):
        os.unlink(f)
    fp.file_number = 0
    fp.enable.value = True
    yield

    fp.enable.value = False
        
    
    
def record_rot():
    """
    A simple test that rotates rot from 0-30 in 2 deg steps
    """
    for j, theta in enumerate(np.linspace(0, 30, 16, endpoint=True)):
        with rolling_record_motion(cam.tiff1, j):
            rot.set(theta, wait=True)

def simple_rotation():
    rot.set(0, wait=True)
    rot.set(5, wait=True)
    rot.set(0, wait=True)

def run_test(func, count, record_file, fp, fname='claw'):
    record_file = os.path.abspath(record_file)
    run_number = 0
    with open(record_file, 'r') as fin:
        for l in fin:
            run_number += 1
    
    base_path = os.path.join(os.path.dirname(record_file), 
                             'movies'
                             '{:05d}'.format(run_number),
                             '00')
    fp.file_path = base_path
    fp.file_name = fname
    success_count = 0
    try:
        for j in range(count):
            print("starting round {j} of {c}".format(j=j, c=count))
            with rolling_record_motion(fp, j):
                func()
            success_count += 1
    except Exception as e:
        # log the exception to disk someplace
        print(e)
        pass
        fail = 1
    else:
        # clean up files if we succedded
        pass
        fail = 0
    finally:
        with open(record_file, 'a') as fout:
            fout.write('{:d},{:d},{:d}\n'.format(count, success_count, fail))
        
