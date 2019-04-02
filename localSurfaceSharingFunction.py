# -*- coding: utf-8 -*-
"""
Created on Sat Mar 30 15:22:34 2019

@author: Alan
"""
from luFunctions import clock_msg
from alanFunctions import xyBounds
import salan_dbscan
import numpy as np
import open3d
from matplotlib.pyplot import cm
from matplotlib import pyplot as plt
import bisect
import time

global color, debug
debug = False

class Element():
    def __init__(self,k,i,j,xyz,norms,color,zMin,zMax,bounds):
        self.k = k
        self.x = i
        self.y = j
        self.points = xyz
        self.normals = norms
        self.color = color
        self.zMin = zMin
        self.zMax = zMax
        self.bounds = bounds
        
        #Holds an array of z values of the lower bound of planar surfaces
        
        self.surf = []
        
        #Holds surf values stolen from adjacent nodes that did not exist 
        #in the elements area and have not been clustered yet
        self.surfTemp = []
        
        
        self.empty = False
        if xyz.size == 0:
            self.empty = True
        #self.clusterSurf()
    def clusterSurf(self):
        if not self.empty:
            index = self.normals[:,2]>0.99
            surfPoints = self.points[index,:]
            nb = 50
            hist = np.histogram(surfPoints[:,2],range=(0.5*(self.zMax-self.zMin)+self.zMin,self.zMax), bins=nb)
            ind = hist[0]>300*(50/nb)
            pos = np.where(ind)[0]
            counter = 1
            j = 0
            while 1:
                if j+1 >= len(pos):
                    break
                #if adjacent box is non zero, delete the box to the right and look again
                if (pos[j+1]==pos[j]+counter):
                    counter += 1
                    pos = np.delete(pos,j+1)
                #otherwise look to next box
                else:
                    j+=1
                    counter = 1
            for k in range(len(pos)):
                self.surf.append(hist[1][pos[k]])
            
            
            
    def export(self,k,color):
        #print("I'm not done yet")
        filename = "../data/elements/cluster" + str(k) + "_" + str(self.x) + "," + str(self.y) + ".pcd"
        pcd_export = open3d.PointCloud()
        pcd_export.points = open3d.Vector3dVector(self.points)
        rgb = np.matmul(np.ones((len(self.points),3)),np.diag(color))
        pcd_export.colors = open3d.Vector3dVector(rgb)
        open3d.write_point_cloud(filename, pcd_export)
def extractIndex(data, bounds):
    r1 = data[:,0]>=bounds[0]
    r2 = data[:,0]<=bounds[1]
    r3 = data[:,1]>=bounds[2]
    r4 = data[:,1]<=bounds[3]
    index = (r1 & r2 & r3 & r4)
    return index
def histCluster(points,zMin,zMax,surf):
    
    res = []
    nb = 50
    dz = zMax-zMin
    hist = np.histogram(points,range=(0.5*(dz)+zMin,zMax), bins=nb)
    
    #hist = plt.hist(points,range=(0.5*(dz)+zMin,zMax), bins=nb)
    ind = hist[0]>0
    pos = np.where(ind)[0]
    posRight = pos
    posLeft = pos
    counter = 1
    j = 0
    while 1:
        if j+1 >= len(posLeft):
            break
        #if adjacent box is non zero, delete the box to the right and look again
        if (posLeft[j+1]==posLeft[j]+counter):
            counter += 1
            posLeft = np.delete(posLeft,j+1)
        #otherwise look to next box
        else:
            j+=1
            counter = 1
            
    counter = 1
    j = len(posRight)-1
    while 1:
        if j-1 < 0:
            break
        #if adjacent box is non zero, delete the box to the right and look again
        if (posRight[j-1]==posRight[j]-counter):
            counter -= 1
            posRight = np.delete(posRight,j-1)
            j-=1
        #otherwise look to next box
        else:
            j-=1
            counter = 1
    #for each
    if debug:
        print("Pos= " + str(pos))
        print("PosLeft= " + str(posLeft))
        print("PosRight= " + str(posRight))
    for k in range(len(posLeft)):
        left = hist[1][posLeft[k]]
        right = hist[1][posRight[k]]
        if left==right:
            right = hist[1][posRight[k]+1]
        rb = ((left,right))
        index = (points>=rb[0]) & (points<=rb[1])
        pSub = points[index]
        
        #if {e.surf} in {pSub} -> continue
        index2 = ((surf>left-dz/10)&(surf<right+dz/10))
        if debug:
            print("Left=%3.3f\tRight=%3.3f\t"%(left,right))
            print("psub = " + str(pSub))
            print("index = " + str(index))
            print("index2 = " + str(index2))
        
        if np.any(index2):
            #print("Continuing because surface already exists")
            continue
        if len(pSub)==0:
            #print("Continuing because no points found in surfTemp to append")
            continue
        #print(pSub)
        result = (np.max(pSub)-np.min(pSub))/2+np.min(pSub)
        #print("Appending %3.3f to surf"%result)
        res.append(result)
    return res
        
    
    #return a list of z values for the lower bound of each cluster

def spreadNeighbors(k,x,y,e,eMat,dx,dy,nx,ny,zMin,zMax):
    #for each adjacent element
        #np.append(adjacent element surfTemp, element surf)
    #print("k=%d\tx=%d\ty=%d\t"%(k,x,y))
    x_indices = np.arange(x-dx,x+dx+1)
    x_indices = x_indices[(x_indices>=0) & (x_indices<nx)]
    y_indices = np.arange(y-dy,y+dy+1)
    y_indices = y_indices[(y_indices>=0) & (y_indices<ny)]
    for i in x_indices:
        for j in y_indices:
            if not (i==x and j==y):
                #print("k=%d\ti=%d\tj=%d\t"%(k,i,j))
                eMat[k][i][j].surfTemp = np.append(eMat[k][i][j].surfTemp,e.surf)
def updateSurf(e, zMin, zMax):
    if debug:
        if len(e.surf)<2:
            print("*"*100)
        print("e.surf = " +str(e.surf))
        print("e.surfTemp = " +str(e.surfTemp))
    e.surfTemp = histCluster(e.surfTemp,zMin,zMax,e.surf)
    changed = len(e.surfTemp)
    e.surf = np.append(e.surf,e.surfTemp)
    e.surf.sort()
    return changed

'''
def mergeNeighbors(k,x,y,e,eMat,dx,dy,nx,ny,zMin,zMax):
    e.surfTemp = []
    x_indices = np.arange(x-dx,x+dx+1)
    x_indices = x_indices[(x_indices>=0) & (x_indices<nx)]
    y_indices = np.arange(y-dy,y+dy+1)
    y_indices = y_indices[(y_indices>=0) & (y_indices<ny)]
    for i in x_indices:
        for j in y_indices:
            if not (i==x and j==y):
                #print("k=%d\ti=%d\tj=%d\t"%(k,i,j))
                e.surfTemp = np.append(e.surfTemp,eMat[k][i][j].surf)
                #e.surfTemp.append(eMat[k][i][j].surf)
            
    #print("k=%d\tx=%d\ty=%d\t"%(k,x,y))
    #print("e.surf before:" + str(e.surf))
    #print("e.surfTemp before:" + str(e.surfTemp))
    
    e.surfTemp = histCluster(e.surfTemp,zMin,zMax,e.surf)
    #print("e.surfTemp after:" + str(e.surfTemp))
    e.surf = np.append(e.surf,e.surfTemp)
    e.surf.sort()
    return e.surf
    
    #e.surfTemp now has most likely multiples of the surfaces missing originally
    #how to cluster them...
'''
def createSurfPCD(nx,ny,eMat, cluster):    
    flag = False       
    for k in range(len(cluster)):
        for x in range(ny):
            for y in range(nx):
                surf = eMat[k][x][y].surf
                bounds = eMat[k][x][y].bounds
                cx = (bounds[1]-bounds[0])/2+bounds[0]
                cy = (bounds[3]-bounds[2])/2+bounds[2]
                if not flag:
                    for n in range(len(surf)):
                        surfPCD =  np.array((cx,cy,surf[n]))
                        flag = True
                else:
                    for n in range(len(surf)):
                        surfPCD = np.vstack((surfPCD,np.array((cx,cy,surf[n]))))
                
                #if len(surf)==1:
                    #print("x=%d\tx=%d\ty=%d\t"%(k,x,y),end="")
                    #print(surf)
    return surfPCD

def createSurfTempPCD(nx,ny,eMat, cluster):
    flag = False       
    for k in range(len(cluster)):
        for x in range(ny):
            for y in range(nx):
                surf = eMat[k][x][y].surfTemp
                bounds = eMat[k][x][y].bounds
                cx = (bounds[1]-bounds[0])/2+bounds[0]
                cy = (bounds[3]-bounds[2])/2+bounds[2]
                if not flag:
                    for n in range(len(surf)):
                        surfPCD =  np.array((cx,cy,surf[n]))
                        flag = True
                else:
                    for n in range(len(surf)):
                        surfPCD = np.vstack((surfPCD,np.array((cx,cy,surf[n]))))
                
                #if len(surf)==1:
                    #print("x=%d\tx=%d\ty=%d\t"%(k,x,y),end="")
                    #print(surf)
    return surfPCD
def exportComponents(deck,pierCap, pier):
    red = np.diag(np.divide([255, 0, 0],255))
    blue = np.diag(np.divide([0, 0, 255],255))
    green = np.diag(np.divide([0, 255, 0],255))
    pcd_export = open3d.PointCloud()
    pcd_export.points = open3d.Vector3dVector(deck)
    rgb = np.matmul(np.ones((len(deck),3)),red)
    pcd_export.colors = open3d.Vector3dVector(rgb)
    open3d.write_point_cloud("../data/elements/deck.pcd", pcd_export)
    
    pcd_export = open3d.PointCloud()
    pcd_export.points = open3d.Vector3dVector(pierCap)
    rgb = np.matmul(np.ones((len(pierCap),3)),green)
    pcd_export.colors = open3d.Vector3dVector(rgb)
    open3d.write_point_cloud("../data/elements/pierCap.pcd", pcd_export)
    
    pcd_export = open3d.PointCloud()
    pcd_export.points = open3d.Vector3dVector(pier)
    rgb = np.matmul(np.ones((len(pier),3)),blue)
    pcd_export.colors = open3d.Vector3dVector(rgb)
    open3d.write_point_cloud("../data/elements/pier.pcd", pcd_export)
    return 1


def createExportBounds(bounds, k, x, y, ny, nx):
    boundExport = np.zeros((4))
    boundExport[0] = bounds[k][0]+(bounds[k][1]-bounds[k][0])*(x/ny)
    boundExport[1] = bounds[k][0]+(bounds[k][1]-bounds[k][0])*((x+1)/ny)
    boundExport[2] = bounds[k][2]+(bounds[k][3]-bounds[k][2])*(y/nx)
    boundExport[3] = bounds[k][2]+(bounds[k][3]-bounds[k][2])*((y+1)/nx)
    return boundExport

def createEB_x(bounds, k, x, ny):
    boundExport = np.zeros((4))
    boundExport[0] = bounds[k][0]+(bounds[k][1]-bounds[k][0])*(x/ny)
    boundExport[1] = bounds[k][0]+(bounds[k][1]-bounds[k][0])*((x+1)/ny)
    boundExport[2] = bounds[k][2]+(bounds[k][3]-bounds[k][2])
    boundExport[3] = bounds[k][2]+(bounds[k][3]-bounds[k][2])
    return boundExport

def pierAreaSegmentation(pierArea,begining,start,write):    
    print('\n*Loading point cloud')
    #Note: this nx and ny are really nx' and ny'. 
    #They correspond to number of subdivisions per "Pier Cluster"
    nx = 20
    ny = 20
        
    pierSize = 0
    for i in range(len(pierArea)):
        pierSize += len(pierArea[i])
        
    bigPierArea = np.empty((pierSize,3))
    pos = 0
    nex = 0
    for i in range(len(pierArea)):
        nex = len(pierArea[i])
        for j in range(len(pierArea[i])):
            bigPierArea[pos+j,:] = pierArea[i][j,:]
        pos += nex
        
    start = clock_msg('*Compute Normals',start,begining)
    
    pcd = open3d.PointCloud()
    pcd.points = open3d.Vector3dVector(bigPierArea)
    open3d.estimate_normals(pcd, search_param = open3d.KDTreeSearchParamHybrid(radius = 0.1, max_nn = 30))
    normals = np.asarray(pcd.normals)
        
    start = clock_msg('*Cluster by pier group',start,begining)
    
    pcd = open3d.voxel_down_sample(pcd, voxel_size = 0.2)
    xyz= np.asarray(pcd.points)
    plot = False
    cluster, labels = salan_dbscan.hdbscan_fun(xyz,plot)
    
    scale = 0
    bounds = np.zeros((len(cluster),4))
    for k in range(len(cluster)):
        bounds[k] = xyBounds(cluster[k], scale)
    
        
    #Now for each cluster we have: bounds, points, normals
    #Next step: Slice into cubes
    start = clock_msg('*Populate the element objects',start,begining)
    eMat = []
    pierAreaSub = []
    normSub = []
    #pierAreaSubX = []
    #normSubX= []
    plot = False
    if plot:
        fig, ax = plt.subplots()
    for k in range(len(cluster)):
        color = iter(cm.rainbow(np.linspace(0,1,nx*ny)))
        e = [[[] for x in range(nx)] for x in range(ny)]
        zMin = np.min(cluster[k][:,2])
        zMax = np.max(cluster[k][:,2])
        #boundExport = [[np.zeros(4) for x in range(nx)] for x in range(ny)]
        #DeltaX_length = 
        index = extractIndex(bigPierArea,bounds[k])
        pierAreaSub.append(bigPierArea[index,:])
        normSub.append(normals[index,:])
        for x in range(ny):
            #Consider slicing in the x direction before cubing the data
            #time to beat: 1.73 seconds
            #BEx = createEB_x(bounds, k, x, ny)
            #index = extractIndex(bigPierArea,BEx)
            #pierAreaSubX.append(bigPierArea[index,:])
            #normSubX.append(normals[index,:])
            for y in range(nx):
                #print("k=%d\tx=%d\ty=%d\t"%(k,x,y))
                boundExport = createExportBounds(bounds, k, x, y, ny, nx)
                index = extractIndex(pierAreaSub[k], boundExport)
                pointsExport = pierAreaSub[k][index,:]
                normalsExport = normSub[k][index,:]
                e[x][y] = Element(k,x,y,pointsExport,normalsExport,next(color)[0:3],zMin,zMax,boundExport)
                if plot:
                    ax.vlines(boundExport[0],ymin=boundExport[2],ymax=boundExport[3])
                    ax.vlines(boundExport[1],ymin=boundExport[2],ymax=boundExport[3])
                    ax.hlines(boundExport[2],xmin=boundExport[0],xmax=boundExport[1])
                    ax.hlines(boundExport[3],xmin=boundExport[0],xmax=boundExport[1])
        eMat.append(e)
        
    start = clock_msg('*Cluster Element Surfaces',start,begining)
    for k in range(len(cluster)):
        for x in range(ny):
            for y in range(nx):
                eMat[k][x][y].clusterSurf()
                #print(surfPCD)
    
    
    
    
     
      
    surfPCD = createSurfPCD(nx,ny,eMat, cluster)
    
    #Accept surfaces from adjacent dx,dy nodes (adjacent 8 squares if 1,1)
    dx=2
    dy=2
    '''
    k=0
    x=3
    y=2
    mergeNeighbors(k,x,y,eMat[k][x][y],dx,dy,nx,ny)
    '''
    
    #print(surfPCD)
    '''
    start = clock_msg('*Merge neighboring surfaces',start,begining)
    for iterrations in range(1):
        for k in range(len(cluster)):
            for x in range(ny):
                for y in range(nx):
                    eMat[k][x][y].surf = mergeNeighbors(k,x,y,eMat[k][x][y],eMat,dx,dy,nx,ny,zMin,zMax)
        #print(surfPCD)
    '''
    start = clock_msg('*Spread surfaces to neighbors',start,begining)
    for iterrations in range(20):
        
        changed = 0
        for k in range(len(cluster)):
            for x in range(ny):
                for y in range(nx):
                    zMin = np.min(cluster[k][:,2])
                    zMax = np.max(cluster[k][:,2])
                    spreadNeighbors(k,x,y,eMat[k][x][y],eMat,dx,dy,nx,ny,zMin,zMax)
        #SurfTemp export after itteration "itterations"
        surfPCDtemp = createSurfTempPCD(nx,ny,eMat, cluster)
        filename = "../data/elements/surfPCD_temp_" + str(iterrations) + ".pcd"
        pcd_export = open3d.PointCloud()
        color = np.diag(np.divide([255, 0, 0],255))
        rgb = np.matmul(np.ones((len(surfPCDtemp),3)),color)
        pcd_export.colors = open3d.Vector3dVector(rgb)
        pcd_export.points = open3d.Vector3dVector(surfPCDtemp)
        open3d.write_point_cloud(filename, pcd_export) 
        for k in range(len(cluster)):
            for x in range(ny):
                for y in range(nx):
                    zMin = np.min(cluster[k][:,2])
                    zMax = np.max(cluster[k][:,2])
                    changed += updateSurf(eMat[k][x][y], zMin, zMax)
        if changed == 0:
            break
        print("Itteration %d, Changed %d"%(iterrations, changed))
                    
        #print(surfPCD)
    if write:
        start = clock_msg('*Exporting Everything',start,begining)
        
        filename = "../data/elements/surfPCD.pcd"
        pcd_export = open3d.PointCloud()
        pcd_export.points = open3d.Vector3dVector(surfPCD)
        open3d.write_point_cloud(filename, pcd_export)
        filename = "../data/elements/surfPCD.pcd"
        pcd_export = open3d.PointCloud()
        pcd_export.points = open3d.Vector3dVector(surfPCD)
        open3d.write_point_cloud(filename, pcd_export)  
        
        #print("After Merge")
        surfPCDmerged = createSurfPCD(nx,ny,eMat, cluster)
        filename = "../data/elements/surfPCD_merged.pcd"
        pcd_export = open3d.PointCloud()
        color = np.diag(np.divide([0, 255, 0],255))
        rgb = np.matmul(np.ones((len(surfPCDmerged),3)),color)
        pcd_export.colors = open3d.Vector3dVector(rgb)
        pcd_export.points = open3d.Vector3dVector(surfPCDmerged)
        open3d.write_point_cloud(filename, pcd_export) 
        

        
    
    
    
    start = clock_msg('*Subslice the elements into components',start,begining)
    #Next step is to use the surfaces to split the pier, piercap, and deck
    deck = []
    pierCap = []
    pier = []
    flag = True
    B = []
    dz = zMax-zMin
    delta = 0.005
    for k in range(len(cluster)):
        for x in range(ny):
            for y in range(nx):
                B = []
                e = eMat[k][x][y]
                e.points = e.points[np.argsort(e.points[:,2]), :]
                for s in e.surf:
                    B.append(bisect.bisect_left(e.points[:,2],s-dz*delta))
                    #B should be [index lower surf, index upper surf]
                #print("k=%d\tx=%d\ty=%d\tlen(B)=%d\tlen(e.points[:B[0],:])=%d"%(k,x,y,len(B),len(e.points[:B[0],:])))
                if flag:
                    if len(B)==2:
                        pier = e.points[:B[0],:]
                        pierCap = e.points[B[0]:B[1],:]
                        deck = e.points[B[1]:,:]
                        flag = False
                    else:
                        pier = e.points[:B[0],:]
                        deck = e.points[B[0]:,:]
                        flag = False
                        
                else:
                    if len(B)==2:
                        pier = np.vstack((pier,(e.points[:B[0],:])))
                        pierCap = np.vstack((pierCap,(e.points[B[0]:B[1],:])))
                        deck = np.vstack((deck,(e.points[B[1]:,:])))
                    else:
                        pier = np.vstack((pier,(e.points[:B[0],:])))
                        deck = np.vstack((deck,(e.points[B[0]:,:])))

    
    if write:
        exportComponents(deck,pierCap,pier)
    return deck, pierCap, pier, start



'''
begining = time.perf_counter()
start = begining
write = True
print('\nLoading point cloud')
pierArea = np.load("pierArea.npy")

deck, pierCap, pier, start = pierAreaSegmentation(pierArea,begining,start,write)

'''




