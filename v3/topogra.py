from freenect import sync_get_depth as get_depth
import numpy as np
import scipy.linalg
import functools
import scipy.optimize
#import matplotlib.pyplot as plt


PLANE_PARAMS = [0.01,-0.001, 730.]#[0.006452, -0.032609, 712.261579]
SCALE_FACTOR = 1./50


#TODO use BoxLayout.txt? Primary issue is unit scaling 730 -> -96.5


def plane(x, y, params):
    a = params[0]
    b = params[1]
    c = params[2]
    z = a*x + b*y + c
    return z

"""Error function for fitting the planar parameters"""
def error(params, points):
    result = 0
    for (x,y,z) in points:
        plane_z = plane(x, y, params)
        diff = abs(plane_z - z)
        result += diff**2
    return result

"""Read in the AR Sandbox Calibration File"""
def ar_calibration(fname='BoxLayout.txt')
    f = open(fname,'r')
    lines = f.readlines()
    plane = lines[0].split('(')[1].split(')')[0].split(',')
    plane = np.array(plane,dtype=float)
    factor = 730./float(lines[0].split(')')[1])
    vertices = []
    for k in range(1,len(lines)):
        l = lines[k]
        d = l.strip('(')
        d = d.strip(')')
        data = d.split(',')
        vertices.append([float(data[0]), float(data[1]), float(data[2])*factor])
    vertices = np.array(vertices)
    f.close()

    #make the baseplane



"""Given a *.npy file of a saved topography (ideally a flat surface), find the parameters of the 
plane to remove for normalization. Put results in PLANE_PARAMS"""
def init_calib(fname=None, data=None):
    if fname != None:
        data = np.load(fname)
    # best-fit linear plane
    # regular grid covering the domain of the data

    badpx = np.where(data==2047)
    data = data.astype('float32')
    data[badpx] = np.nan
    X,Y = np.meshgrid(np.arange(0,data.shape[1]), np.arange(0,data.shape[0]))
    
    points =     [(10,10,data[10,10]),
                (10,data.shape[0]-10,data[10,-10]),
                (data.shape[1]-10,10,data[-10,10]),
                (data.shape[1]-10,data.shape[0]-10,data[-10,-10]),
                (data.shape[1]/2., data.shape[0]/2.,data[data.shape[1]/2., data.shape[0]/2.])]

    fun = functools.partial(error, points=points)
    params0 = [0, 0, 0]
    res = scipy.optimize.minimize(fun, params0)

    # evaluate calibration plane on grid
    a = res.x[0]
    b = res.x[1]
    c = res.x[2]
    Z = a*X + b*Y + c

    surf = np.copy(data) - Z

    print 'PLANAR_PARAMS =  [%f, %f, %f]'%(a,b,c)


def calibrate(surface, baseplane):
    """Do calibration here - scaling, setting zero point, removing dead pixels, and trimming edges(?)."""
    
    surface = surface.astype('float32')
    #need to remove planar slope
    surface = surface[40:-30, 30:-30] - baseplane
    BAD_PIX = np.where(surface>=200)
    surface *= .1#SCALE_FACTOR
    #scale
    x =  np.power(np.e,np.absolute(surface))
    surface = x * np.absolute(surface) / surface * 10
    #surface -= .25*np.max(surface)
    
    #surface = np.negative(surface)
    surface[BAD_PIX] = 0.#np.nan

    return np.nan_to_num(surface), BAD_PIX

def generate_baseplane(shape=(580,410)):
    """Run on startup to get quick baseplane for calibration using PLANE_PARAMS"""
    X,Y = np.meshgrid(np.arange(0,shape[0]), np.arange(0,shape[1]))
    XX = X.flatten()
    YY = Y.flatten()
    Z = PLANE_PARAMS[0]*X + PLANE_PARAMS[1]*Y + PLANE_PARAMS[2]
    return Z


def update_surface(baseplane,prev=None,FLOOR=-710,verbose=False):
    """Read updated topography and calibrate for use"""
    (depth,_)= get_depth()
    topo,pix = calibrate(depth,baseplane)
    if verbose:
        print 'SURFACE STATS'
        print np.mean(topo), np.max(topo),np.min(topo), np.median(topo)
    #if there are enough pixels above a threshold, ignore and show previous topo
    #this is useful when hands are in the sandbox
    if len(np.where(topo<FLOOR)[0]) + len(np.where(topo<FLOOR)[1]) > 10:
        if prev == None:
            return topo #- np.nanmedian(topo)
        else:
            return topo
    return topo #- np.nanmedian(topo)


#roughly 4.5 units per cm

"""Run the calibration scripts and output a plot showing how well the plane subtraction worked."""
if __name__ == "__main__":
    from sys import argv
    script, fname = argv
    import matplotlib.pyplot as plt
    init_calib(fname)
    baseplane = generate_baseplane()
    test = update_surface(baseplane,None)
    fig = plt.figure()
    plt.imshow(test)
    plt.show()
    #init_calib(data=test)
