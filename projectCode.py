# -*- coding: cp1252 -*-
'''
    Detection of parallelism and semi-parallelism
    between segments of a pair of polylines based on
    an angle of tolerance and a simple distance threshold

    Coding with Python 2.7.10

    Author: Fernando Esquivel
    Version: Feb 14, 2020
'''

# packages to import
import os
import arcpy
import math
import random

# function for defining and accessing the directory
''' this function was created based on lecture notes'''
def createSubdir(workspace, subdirList):

    for subdir in subdirList:

        if not os.path.isdir(workspace + '/' + subdir):
            os.mkdir(os.path.join(workspace, subdir))

# function to enforce the use of the right input extension
''' this function was created based on lecture notes'''
def controlExtension(inName, ext):
    if inName.rfind('.') > 0:
        return inName[:inName.find('.')] + ext
    else:
        return inName + ext

# function to get complete paths to files
''' this function was created based on lecture notes'''
def completePath(workspace, subdir, nameList):
    for ix in range(len(nameList)):
        nameList[ix] = workspace + '/' + subdir + '/' + str(nameList[ix])
    return nameList

# function to check whether a file exists under the given path
''' this function was created based on lecture notes'''
def checkExistence(pathList):
    check = True
    for data in pathList:
        if not arcpy.Exists(data):
            check = False
            print '! dataset ' + data + ' is missing'
            break
    return check

# function to break a polyline into individual segments
''' this function was created based on lecture notes'''
def splitPolylineIntoSegments(inFC, outFC):
    arcpy.SplitLine_management(inFC, outFC)

# function to calculate starting points of segments
''' this function was created based on lecture notes'''
def calculateStartPoints(segFC):
    startPoints = []
    fieldList = ['SHAPE@']
    with arcpy.da.SearchCursor(segFC, fieldList) as cur: 
        for row in cur:
            startPoints.append((row[0].firstPoint.X,row[0].firstPoint.Y))  
    return startPoints

# function to calculate ending points of segments
''' this function was created based on lecture notes'''
def calculateEndPoints(segFC):
    endPoints = []
    fieldList = ['SHAPE@']
    with arcpy.da.SearchCursor(segFC, fieldList) as cur: 
        for row in cur:
            endPoints.append((row[0].lastPoint.X, row[0].lastPoint.Y))
    return endPoints

# function to calculate the slope of segments
''' the loop to create this function was based on documentation from
    https://community.esri.com/thread/20473'''
def getSlope(startPoint, endPoint):
    slope = []
    if len(startPoint) != len(endPoint):
        print '! Warning: lists length not identical.'
        return slope
    for i in range(len(startPoint)):
        pnt0 = startPoint[i]
        pnt1 = endPoint[i]
        if pnt1[1]==pnt0[1] and pnt1[0]==pnt0[0]:
            print '! Warning: this is not a line, it is a point'
            return slope
        else:
            radian = math.atan((pnt1[1] - pnt0[1])/(pnt1[0] - pnt0[0]))
            degrees = radian * 180 / math.pi
            slope.append(degrees)
    return slope

# function to get id (unique values) from the segments
''' the loop to create this function was based on documentation from
    https://gis.stackexchange.com/questions/208430/trying-to-extract-a-list-of-unique-values-from-a-field-using-python'''
def unique_values(table , field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})

# function to detect parallel segments
''' the loop to create this function was based on documentation from
    https://www.geeksforgeeks.org/python-get-key-from-value-in-dictionary/'''
def detectParallelSegments(dicSlope1,dicSlope2):
    comparison = []
    for key, value in dicSlope1.items():
        comparison.append([key2 for key2,value2 in dicSlope2.items()
                       if value==value2])
    for i in comparison:
        if len(i)<1:
            comparison[comparison.index(i)].append(-1)
    return comparison

# function to detect semi-parallel segments
def detectSemiparallelSegments(dicSlope1,dicSlope2):
    comparison = []
    for key, value in dicSlope1.items():
        comparison.append([key2 for key2,value2 in dicSlope2.items()
                       if value!=value2 and abs(value-value2)<=angleOfTolerance])
    for i in comparison:
        if len(i)<1:
            comparison[comparison.index(i)].append(-1)
    return comparison

# function to get the closest segments to another segment based on a threshold
''' the loop to create this function was based on documentation from
    https://desktop.arcgis.com/en/arcmap/10.3/tools/analysis-toolbox/generate-near-table.htm'''
def getClosestSegments(segFC1,segFC2,table,search_radius):   
    location = "NO_LOCATION"
    angle = "NO_ANGLE"
    closest = 'ALL'
    segmentsToGet = 10
    arcpy.GenerateNearTable_analysis(segFC1, segFC2, table, search_radius,
                                     location, angle, closest, segmentsToGet)

# function to create a dictionary with segment of reference and its closest segments
''' the loop to create this function was based on documentation from
    https://desktop.arcgis.com/es/arcmap/10.3/tools/analysis-toolbox/near.htm'''
def createClosestSegmentsDictionary(table):
    keyField = "IN_FID"
    valueField = "NEAR_FID"
    nearest_dict = dict()
    with arcpy.da.SearchCursor(table, [valueField, keyField]) as rows:
        for row in rows:
            nearest_id = row[0]  
            input_id = row[1]     
            if input_id in nearest_dict:
                nearest_dict[input_id].append(nearest_id)
            else:
                nearest_dict[input_id] = [nearest_id]
    return nearest_dict

# function to check if both criteria (angle and distance) are met
def checkCriteria(Segments,closestSegments):
    metCriteria = []
    for key,value in Segments.items():
        metCriteria.extend([list(set(value) & set(value2))
                            for key2,value2 in closestSegments.items()
                            if key==key2])
    for i in metCriteria:
        if len(i)>0:
            metCriteria[metCriteria.index(i)] = i
        else:
            metCriteria[metCriteria.index(i)].append(-1)
    return metCriteria

# function to add a new fields in the attribute table
def addField(segFCs,fieldName,elementType):
    arcpy.AddField_management(segFCs, fieldName, elementType)

# function to assign semi- and parallel segments' id to the attribute table
''' the loop to create this function was based on documentation from
    https://gis.stackexchange.com/questions/230536/adding-values-from-list-to-field-in-feature-class-using-arcpy'''
def insertIds(segFCs,fieldName,fieldName2,parallels,semiparallels):
    pointer = 0
    with arcpy.da.UpdateCursor(segFCs, fieldName) as cursor:
        for row in cursor:
            row[0] = str(parallels[pointer])
            pointer += 1
            cursor.updateRow(row)
    pointer = 0
    with arcpy.da.UpdateCursor(segFCs, fieldName2) as cursor:
        for row in cursor:
            row[0] = str(semiparallels[pointer])
            pointer += 1
            cursor.updateRow(row)

#########################################################################

# instruction to overwrite files
arcpy.env.overwriteOutput = True
# thresholds
distance = "300 Meters"
angleOfTolerance = 15
# inputs
workspace = "C:/finalProject"
subdirList = ["Output", "Shapes", "Table"]
inFCNames = ["line_a.shp","line_b.shp"]
segFCNames = ["seg_a.shp","seg_b.shp"]
fieldName1 = "parallel"
fieldName2 = "semiparal"
type1 = "TEXT"
type2 = "TEXT"
# location path for tables
out_table = workspace + "/Table/near" + str(random.randint(0,100*10))
# creation of directory, subdirectories and path to files
createSubdir(workspace, subdirList)
for i, name in enumerate(inFCNames):
    inFCNames[i] = controlExtension(name, ".shp")
inFCs = completePath(workspace, subdirList[1], inFCNames)
print checkExistence(inFCs)
segFCs = completePath(workspace, subdirList[0], segFCNames)
# split polylines into segments
for i,j in zip(inFCs,segFCs):
    splitPolylineIntoSegments(i,j)
# definition and calculation of starting and ending points
startPoints_a = calculateStartPoints(segFCs[0])
startPoints_b = calculateStartPoints(segFCs[1])
endPoints_a = calculateEndPoints(segFCs[0])
endPoints_b = calculateEndPoints(segFCs[1])
# creation of lists with id of segments
ids_a = unique_values(segFCs[0],'FID')
ids_b = unique_values(segFCs[1],'FID')
# creation of dictionaries with segment id and its corresponding slope
dicSlope_a = dict(zip(ids_a,getSlope(startPoints_a,endPoints_a)))
dicSlope_b = dict(zip(ids_b,getSlope(startPoints_b,endPoints_b)))
# creation of dictionaries with parallel and semi-parallel segments 
dicParallelSegments = dict(zip(ids_a,
                               detectParallelSegments(dicSlope_a,dicSlope_b)))
dicSemiparallelSegments = dict(zip(ids_a,
                                   detectSemiparallelSegments(dicSlope_a,dicSlope_b)))
# identification of closests segments based on a threshold
getClosestSegments(segFCs[0],segFCs[1],out_table,distance)
# creation of a dictionary with segment id and closest segments id
dicClosestSegments = createClosestSegmentsDictionary(out_table)
# verifification that both criteria (distance and angle of tolerance) are met 
metParallelCriteria = checkCriteria(dicParallelSegments,dicClosestSegments)
metSemiparallelCriteria = checkCriteria(dicSemiparallelSegments,dicClosestSegments)
# addition of fields in the attribute table
addField(segFCs[0],fieldName1,type1)
addField(segFCs[0],fieldName2,type2)
# insert id of parallel and semi-parallel segments in the attrubute table
insertIds(segFCs[0],fieldName1,fieldName2,
          metParallelCriteria,metSemiparallelCriteria)

