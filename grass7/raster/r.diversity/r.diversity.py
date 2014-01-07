#!/usr/bin/env python
# -*- coding: utf-8 -*-

############################################################################
#
# MODULE:     r.diversity
# AUTHOR(S):  Luca Delucchi
# PURPOSE:    It calculates the mostly used indices of diversity based on
#             information theory
#
# COPYRIGHT: (C) 2010-2012 by Luca Delucchi
#
#        This program is free software under the GNU General Public
#        License (>=v2). Read the file COPYING that comes with GRASS
#        for details.
#
#############################################################################

#%module
#% description: Calculate diversity indices based on a moving window using r.li packages
#% keywords: raster
#%end
#%option
#% key: input
#% type: string
#% gisprompt: old,cell,raster
#% key_desc: name
#% description: Name of input raster map
#% required: yes
#%end
#%option
#% key: prefix
#% type: string
#% gisprompt: new,cell,raster
#% key_desc: name
#% description: Prefix for output raster map(s)
#% required: yes
#%end
#%option
#% key: alpha
#% type: double
#% key_desc: alpha value for Renyi entropy
#% description: Order of generalized entropy (> 0.0; undefined for 1.0)
#% multiple: yes
#% required: no
#%end
#%option
#% key: size
#% type: integer
#% key_desc: moving window
#% multiple: yes
#% description: Size of processing window (odd number only)
#% answer: 3
#% required: no
#%end
#%option
#% key: method
#% type: string
#% key_desc: method
#% options: simpson,shannon,pielou,renyi
#% multiple: yes
#% description: Name of methods to use
#% required: no
#%end
#%option
#% key: exclude
#% type: string
#% key_desc: exclude method
#% options: simpson,shannon,pielou,renyi
#% multiple: yes
#% description: Exclude methods
#% required: no
#%end


# import library
import os
import sys
import grass.script as grass


# main function
def main():
    # set the home path
    home = os.path.expanduser('~')
    rlidir = os.path.join(home, '.grass7', 'r.li')
    # check if GISBASE is set
    if "GISBASE" not in os.environ:
        # return an error advice
        grass.fatal(_("You must be in GRASS GIS to run this program."))

    # input raster map
    map_in = options['input']
    # output raster map
    map_out = options['prefix']
    # resolution of moving windows
    res = options['size']
    # alpha value for r.renyi
    alpha = options['alpha']
    # method to use
    methods = options['method']
    # excluded method
    excludes = options['exclude']

    resolution = checkValues(res)

    if alpha != '':
        alpha_value = checkValues(alpha, True)

    # check if ~/.r.li path exists
    if not os.path.exists(rlidir):
        # create ~/.grass7/r.li
        os.mkdir(rlidir)

    # set overwrite
    overwrite = grass.overwrite()

    quiet = True

    if grass.verbosity() > 2:
        quiet = False
    # if method and exclude option are not null return an error
    if methods != '' and excludes != '':
        grass.fatal(_("You can use method or exclude option not both"))
    # if method and exclude option are null calculate all module
    elif methods == '' and excludes == '':
        # check if alpha_value is set, else return an error
        if alpha_value == '':
            grass.fatal(_("Please you must set alpha value for Renyi entropy"))
        calculateAll(rlidir, map_in, map_out, resolution, alpha_value, quiet,
                     overwrite)
    # calculate method
    elif methods != '':
        methods = methods.split(',')
        checkAlpha(methods, alpha_value)
        calculateM(rlidir, map_in, map_out, resolution, alpha_value, methods,
                   quiet, overwrite)
    # calculate not excluded index
    elif excludes != '':
        excludes = excludes.split(',')
        checkAlpha(excludes, alpha_value, True)
        calculateE(rlidir, map_in, map_out, resolution, alpha_value, excludes,
                   quiet, overwrite)
    # remove configuration files
    removeConfFile(resolution, rlidir)
    print 'All works are terminated'


# calculate all index
def calculateAll(home, map_in, map_out, res, alpha, quiet, overw):
    # for each resolution create the config file and calculate all index
    for r in res:
        createConfFile(r, map_in, home)
        r = str(r)
        grass.run_command('r.li.simpson', input=map_in, output=map_out + \
                          '_simpson_size_' + r, conf='conf_diversity_' + r,
                          quiet=quiet, overwrite=overw)
        grass.run_command('r.li.shannon', input=map_in, output=map_out + \
                          '_shannon_size_' + r, conf='conf_diversity_' + r,
                          quiet=quiet, overwrite=overw)
        grass.run_command('r.li.pielou', input=map_in, output=map_out + \
                          '_pielou_size_' + r, conf='conf_diversity_' + r,
                          quiet=quiet, overwrite=overw)
        for alp in alpha:
            grass.run_command('r.li.renyi', input=map_in, output=map_out + \
                              '_renyi_size_' + r + '_alpha_' + str(alp),
                              conf='conf_diversity_' + r, alpha=alp,
                              quiet=quiet, overwrite=overw)


# calculate only method included in method option
def calculateM(home, map_in, map_out, res, alpha, method, quiet, overw):
    # for each resolution create the config file
    for r in res:
        createConfFile(r, map_in, home)
        r = str(r)
        # for each method in method option calculate index
        for i in method:
            if i == 'renyi':
                for alp in alpha:
                    grass.run_command('r.li.renyi', input=map_in,
                                      output=map_out + '_renyi_size_' + r + \
                                      '_alpha_' + str(alp), alpha=alp,
                                      conf='conf_diversity_' + r,
                                      quiet=quiet, overwrite=overw)
                else:
                    grass.run_command('r.li.' + i, input=map_in,
                                      output=map_out + '_' + i + '_size_' + r,
                                      conf='conf_diversity_' + r,
                                      quiet=quiet, overwrite=overw)


# calculate only method excluded with exclude option
def calculateE(home, map_in, map_out, res, alpha, method, quiet, overw):
    # set a tuple with all index
    methods = ('simpson', 'shannon', 'pielou', 'renyi')
    # for each resolution create the config file
    for r in res:
        createConfFile(r, map_in, home)
        r = str(r)
        # for each method
        for i in methods:
            # if method it isn't in exclude option it is possible to calculate
            if method.count(i) == 0:
                if i == 'renyi':
                    for alp in alpha:
                        grass.run_command('r.li.renyi', input=map_in,
                                          output=map_out + '_renyi_size_' + r \
                                          + '_alpha_' + str(alp), alpha=alp,
                                          conf='conf_diversity_' + r,
                                          quiet=quiet, overwrite=overw)
        else:
                grass.run_command('r.li.' + i, input=map_in, output=map_out \
                                  + '_' + i + '_size_' + r,
                                  conf='conf_diversity_' + r,
                                  quiet=quiet, overwrite=overw)


# check if alpha value it's set when renyi entropy must be calculate
def checkAlpha(method, alpha_val, negative=False):
    for alpha in alpha_val:
        # it's used when we check the exclude option
        if negative:
            if method.count('renyi') != 1 and alpha == '':
                grass.fatal(_("Please you must set alpha value for Renyi entropy"))
        # it's used when we check the method option
        else:
            if method.count('renyi') == 1 and alpha == '':
                grass.fatal(_("Please you must set alpha value for Renyi entropy"))

#create configuration file instead using r.li.setup
def createConfFile(res, inpumap, home):
    # set the name of conf file
    name = 'conf_diversity_' + str(res)
    confilename = os.path.join(home, name)
    # start the text for the conf file
    outputLine = ['SAMPLINGFRAME 0|0|1|1\n']
    # return r.info about input file
    rinfo = grass.raster_info(inpumap)
    # calculate number of lines
    rows = (rinfo["north"] - rinfo["south"]) / rinfo['nsres']
    # calculate number of columns
    columns = (rinfo['east'] - rinfo['west']) / rinfo['ewres']
    # value for row
    rV = int(res) / rows
    # value for column
    cV = int(res) / columns
    # append the text for the conf file
    outputLine.append('SAMPLEAREA -1|-1|' + str(rV) + '|' + str(cV) + '\n')
    outputLine.append('MOVINGWINDOW\n')
    # open configuration file
    fileConf = open(confilename, 'w')
    # write file
    fileConf.writelines(outputLine)
    # close file
    fileConf.close()


# return a list of resolution
def checkValues(res, alpha=False):
    # check if more values are passed
    if res.count(',') == 1:
        typ = 'values'
        reso = res.split(',')
    # check if a range of values are passed
    elif res.count('-') == 1:
        typ = 'range'
        reso = res.split('-')
    # else only a value is passed
    else:
        typ = 'value'
        reso = [res]
    # transform string to int and check if is a odd number
    for i in range(len(reso)):
        # check if is a odd number
        reso[i] = float(reso[i])
        if reso[i] % 2 == 0:
            # return the error advice
            grass.fatal(_("The size/alpha setting must be an integer number " \
                          "(found %d)" % reso[i]))
    # create a range
    if typ == 'range':
        if alpha:
            grass.fatal(_("Range for alpha values it isn't supported"))
        else:
            reso = range(reso[0], reso[1] + 1, 2)
    return reso


def removeConfFile(res, home):
    for r in res:
        confilename = os.path.join(home, 'conf_diversity_' + str(r))
        os.remove(confilename)

if __name__ == "__main__":
    options, flags = grass.parser()
    sys.exit(main())

