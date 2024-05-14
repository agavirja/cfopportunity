import numpy as np
from shapely.geometry import Polygon

def circle_polygon(metros,lat,lng):
    grados   = np.arange(-180, 190, 10)
    Clat     = ((metros/1000.0)/6371.0)*180/np.pi
    Clng     = Clat/np.cos(lat*np.pi/180.0)
    theta    = np.pi*grados/180.0
    longitud = lng + Clng*np.cos(theta)
    latitud  = lat + Clat*np.sin(theta)
    return Polygon([[x, y] for x,y in zip(longitud,latitud)])
