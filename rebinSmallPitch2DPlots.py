#!/usr/bin/env python
from ROOT import *
import sys
import re
from optparse import OptionParser

# options

parser = OptionParser()
parser.add_option("-i", "--file", dest="inputFile",
                  help="input file")
(arguments, args) = parser.parse_args()

if not arguments.inputFile:
    print "please specify input file";
    sys.exit(0)

gROOT.SetBatch()


PIXEL_HEIGHT = 4
PIXEL_WIDTH  = 6

###############################################################################

    #functions

def getBinData(plot, col, row):
    content = plot.GetBinContent(col+1,row+1)
    error = plot.GetBinError(col+1,row+1)
    return (content, error)

def fillPixel(plot, stretchFactor, startX, startY, content, error):
    for x in range(PIXEL_WIDTH*stretchFactor):
        for y in range(PIXEL_HEIGHT/stretchFactor):
            binX = 1 + startX + x
            binY = 1 + startY + y
            plot.SetBinContent(binX,binY,content)
            plot.SetBinError(binX,binY,error)

def fillRow(plot, rescaledPlot, row, startY, stretchFactor):
    currentX = 0
    currentY = startY
    for col in range(plot.GetNbinsX()):
        content, error = getBinData(plot,col,row)
        if col != 0:
            if col%stretchFactor is 0:  # need to move right and back down
                currentX += PIXEL_WIDTH*stretchFactor
                currentY = startY
            else: # need to move up
                currentY += PIXEL_HEIGHT/stretchFactor
        fillPixel(rescaledPlot, stretchFactor, currentX, currentY, content, error)


# fill in units of 25um to account for various pixel sizes
def rescalePlot(plot):
    # 25 um = 1
    # 50 um = 2
    # 100um = 4
    # 150um = 6
    # 300um = 12
    # 600um = 24

    # 100x150 um = 4x6  bins
    #  50x300 um = 2x12 bins
    #  25x600 um = 1x24 bins


    # active sensor area is 7.8mm (x) by 8.0mm (y) = 312 x 320
    rescaledPlot = TH2D(plot.GetName(),plot.GetTitle(),312,0,312,320,0,320);

    # start at the bottom
    currentY = 0
 
    # fill the first 20 rows of 100x150um pixels
    stretchFactor = 1
    for row in range(20):
        fillRow(plot, rescaledPlot, row, currentY, stretchFactor)
        currentY += PIXEL_HEIGHT

    # fill the next 30 rows of 50x300um pixels
    stretchFactor = 2
    for row in range(20,50):
        fillRow(plot, rescaledPlot, row, currentY, stretchFactor)
        currentY += PIXEL_HEIGHT

    # fill the next 30 rows of 25x600um pixels
    stretchFactor = 4
    for row in range(50,80):
        fillRow(plot, rescaledPlot, row, currentY, stretchFactor)
        currentY += PIXEL_HEIGHT

    rescaledPlot.SetMaximum(plot.GetMaximum())
    rescaledPlot.SetMinimum(plot.GetMinimum())

    return rescaledPlot

###############################################################################


inputFile = TFile(arguments.inputFile)
inputFile.cd()
outputFile = TFile(arguments.inputFile.split(".")[0]+"_Rebinned.root","RECREATE")
outputFile.cd()

# loop over all histograms in input directory
# copy the 1D plots and rebin the 2D plots
# save in new file with "_Rebinned" added to name
for dirKey in inputFile.GetListOfKeys():
    if (dirKey.GetClassName() != "TDirectoryFile"):
        continue
    dir = dirKey.GetName() 
    inputFile.cd(dir)
    outputFile.mkdir(dir)
    for plotKey in gDirectory.GetListOfKeys():
         if re.match ('TH1', plotKey.GetClassName()): # found a 1-D histogram
             plotName = plotKey.GetName()
             plot = inputFile.Get(dir+"/"+plotName)
             outputFile.cd(dir)
             plot.Write()
         if re.match ('TH2', plotKey.GetClassName()): # found a 2-D histogram             
             plotName = plotKey.GetName()
             plot = inputFile.Get(dir+"/"+plotName)
             rescaledPlot = rescalePlot(plot)
             outputFile.cd(dir)
             rescaledPlot.Write()





