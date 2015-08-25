#!/usr/bin/env python

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

from ROOT import *
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

# 
def splitDistribution(twoDplot,oneDplot):

    nbins = oneDplot.GetXaxis().GetNbins()
    xmin = oneDplot.GetXaxis().GetXmin()
    xmax = oneDplot.GetXaxis().GetXmax()
    name = oneDplot.GetName()

    h100x150 = TH1F(name+"100x150",name,nbins,xmin,xmax)
    h50x300 = TH1F(name+"50x300",name,nbins,xmin,xmax)
    h25x600 = TH1F(name+"25x600",name,nbins,xmin,xmax)
    SetOwnership(h100x150, False)
    SetOwnership(h50x300, False)
    SetOwnership(h25x600, False)

    h100x150.SetLineColor(kRed)
    h100x150.SetLineWidth(2)
    h50x300.SetLineColor(kBlue)
    h50x300.SetLineWidth(2)
    h25x600.SetLineColor(kGreen)
    h25x600.SetLineWidth(2)
    oneDplot.SetLineColor(kBlack)
    oneDplot.SetLineWidth(3)



    legend = TLegend(0.6666667,0.6575053,0.8994253,0.9006342)
    SetOwnership(legend, False)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.AddEntry(h100x150,"100#times150 #mum","L")
    legend.AddEntry(h50x300,"50#times300 #mum","L")
    legend.AddEntry(h25x600,"25#times600 #mum","L")
    legend.AddEntry(oneDplot,"total","L")

    for x in range(1,twoDplot.GetNbinsX()+1):
        for y in range(1,twoDplot.GetNbinsY()+1):
            content = twoDplot.GetBinContent(x,y)
            if y <= 20:
                h100x150.Fill(content)
            elif y <= 50:
                h50x300.Fill(content)
            else:
                h25x600.Fill(content)

    canvas = TCanvas(name,"")
    oneDplot.Draw()
    h100x150.Draw("same")
    h50x300.Draw("same")
    h25x600.Draw("same")
    legend.Draw("same")

    return canvas

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
             # for 1D distributions of 2D plots, split into 3 by pixel size
             # and save resulting canvas to file
             if plotName.startswith("dist_"):
                 twoDPlot = inputFile.Get(dir+"/"+plotName.split("dist_")[1])
                 splitPlotCanvas = splitDistribution(twoDPlot,plot)
                 splitPlotCanvas.Write()
             # for regular 1D plots, copy them into the output file
             else:
                 plot.Write()
         if re.match ('TH2', plotKey.GetClassName()): # found a 2-D histogram             
             plotName = plotKey.GetName()
             plot = inputFile.Get(dir+"/"+plotName)
             outputFile.cd(dir)
             # for ROC plots, split into three components
             if plot.GetNbinsX() == 52 and plot.GetNbinsY() == 80:
                 rescaledPlot = rescalePlot(plot)
                 rescaledPlot.Write()
             # for regular 2D plots, copy them into the output file
             else:
                 plot.Write()




