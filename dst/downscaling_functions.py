# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 10:08:49 2019
@author: mariaw

Functions for the climaproof downscaling tool
--> downscaling of model and observational data from 0.1° to 0.01°

This script uses python 3 (python3 environment of miniconda)!
"""

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xesmf as xe
from scipy import ndimage as nd
import warnings; warnings.simplefilter('ignore')

from netCDF4 import Dataset
from netCDF4 import date2num, num2date
from datetime import datetime, timedelta
import os

def check_domain(data, lat_min, lat_max, lon_min, lon_max):
    '''
    Check if specified domain is inside model domain.
    '''
    err = 0
    if (lat_min < data.lat.min()) | (lat_max > data.lat.max()) | (lon_min < data.lon.min()) | (lon_max > data.lon.max()):
        err = 1   
    return err

def cut_domain(ds, lat_min, lat_max, lon_min, lon_max, start_y=0, end_y=0):
    err = check_domain(ds, lat_min, lat_max, lon_min, lon_max)
    
    if err == 0:
        ds_cut = ds.where(((ds['lon'] >= lon_min) & (ds['lon'] <= lon_max) & (ds['lat'] >= lat_min) & (ds['lat'] <= lat_max)), drop=True)
        
        if (start_y == 0) | (end_y == 0):
            return ds_cut        
        else:
            try:
                ds_cut = ds_cut.sel(time=slice(str(start_y)+'-01-01', str(end_y)+'-12-31'))
            except(ValueError):
                ds_cut = ds_cut.sel(time=slice(str(start_y)+'-01-01', str(end_y)+'-12-30'))
    else:
        print("Your specified lat/lon values are outside the model domain. Please choose different lat/lon values.")
        return
    
    return ds_cut

def linreg(data, topo, plot_opt=False):
    # remove nans
    nans = np.isnan(data)
    data_reg = data[~nans]
    topo_reg = topo[~nans]   
    # linear regression
    A = np.vstack([topo_reg, np.ones(len(data_reg))]).T
    linreg = np.linalg.lstsq(A, data_reg, rcond=None)
    gradient ,constant = linreg[0]
    
    if plot_opt == True:
        #testplot of regression
        plt.figure()
        plt.scatter(topo, data)
        plt.plot(gradient*np.arange(0,2200,1)+constant, color='red')
    
    return gradient , constant

def fill(data, topo_mask, invalid=None):
    """
    Replace the value of invalid 'data' cells (indicated by 'invalid') 
    by the value of the nearest valid data cell

    Input:
        data:    numpy array of any dimension
        invalid: a binary array of same shape as 'data'. True cells set where data
                 value should be replaced.
                 If None (default), use: invalid  = np.isnan(data)

    Output: 
        Return a filled array. 
    """
    #import numpy as np
    #import scipy.ndimage as nd

    if invalid is None: invalid = np.isnan(data)

    ind = nd.distance_transform_edt(invalid, return_distances=False, return_indices=True)
    
    data_filled = data[tuple(ind)]
    
    data_masked = data_filled * topo_mask
    
    data_masked[:,~topo_mask] = -9999
    
    return data_masked

def regrid_data(data, topo_coarse, topo_fine, variable, regrid_method = 'patch'):
    
    if (variable == 'tasmax') | (variable == 'tasmin') | (variable == 'rsds') | (variable == 'sfcWind') | (variable == 'hurs'):
        # remove height dependency before regridding and add afterwards
        try:
            data.coords['month'] = data['time.month']
        except(AttributeError):
            data.coords['month'] = data['time.dt.month']
        
        grad = np.zeros((12,1))*np.nan
        c = np.zeros((12,1))*np.nan
        
        topo_1d = topo_coarse['height'].data.reshape(np.size(topo_coarse['height']),1)
        
        data_det = data.copy(deep=True)
        
        for month in range(0,12):
            
            # get data for month
            month_data = data[variable][data['month']==month+1,:,:]
            month_mean = month_data.mean(dim='time', skipna=True)  
            data_1d = month_mean.data.reshape(np.size(month_mean),1)
            
            grad[month], c[month] = linreg(data_1d, topo_1d)
            
            data_det[variable][data['month']==month+1,:,:] = month_data - (grad[month]* topo_coarse['height'])  
            
        regridder = xe.Regridder(data_det, topo_fine, regrid_method)
        data_regrid_tmp = regridder(data_det[variable])
        
        import ipdb; ipdb.set_trace()
        data_masked = correct_coast(data_regrid_tmp.data, topo_fine)
        
        data_regrid = np.ones_like(data_regrid_tmp)*np.nan
        for month in range(0,12):
            print(month)
            data_regrid[data['month']==month+1,:,:] = data_masked[data['month']==month+1,:,:] + (grad[month]* topo_fine['height'].data)  
            
    else:    
        regridder = xe.Regridder(data, topo_fine, regrid_method)
        data_regrid_tmp = regridder(data[variable])  
        
        data_regrid = correct_coast(data_regrid_tmp.data, topo_fine)
    
    if variable == 'pr':
        # set eventual negative values to 0
        data_regrid[data_regrid<0] = 0
    
    regridder.clean_weight_file()
    
    return data_regrid
    
def correct_coast(data_regrid, topo_fine):
    # data_regrid: numpy array
    # topo_fine: data_set
    
    # correct coastal grid points, that are not resolved after regridding from coarse to fine resolution
    topo_mask = ~np.isnan(topo_fine['height'].data)
    #mask = (np.isnan(data_regrid[0,:,:]) & ~np.isnan(topo_fine['height']))
    
    data_masked = fill(data_regrid, topo_mask)
        
    return data_masked

# functions for writing netcdf
def get_ncattrs(fn_nc):
    nc_fid = Dataset(fn_nc, 'r')
    model_cal = str(nc_fid.variables['time'].calendar)
    model_name = str(nc_fid.getncattr('modelname'))
    return model_cal, model_name

def write_netcdf(array3d, param_name, lat1d, lon1d, start_year, end_year, savedir, filename, model_name, cal='gregorian'):#, freq ='daily'):    
    
    # create netCDF file
    savename = savedir+filename+'_'+str(start_year)+'-'+str(end_year)+'.nc'
    # check if file already exists - if yes, delete it before writing new file
    if os.path.exists(savename):
        os.remove(savename)
    
    # open new netCDF file in write mode:   
    try:
        dataset = Dataset(savename,'w',format='NETCDF4_CLASSIC')
    except(IOError):
        os.remove(savename)
        dataset = Dataset(savename,'w',format='NETCDF4_CLASSIC')
    # create dimensions
       
    dataset.createDimension("time",None)
    dataset.createDimension("lat", len(lat1d))
    dataset.createDimension("lon",len(lon1d))
    
    # create variables
    times = dataset.createVariable("time","f8",("time",))
    lats = dataset.createVariable("lat","f4",("lat",))
    lons = dataset.createVariable("lon","f4",("lon",))
    var = dataset.createVariable(param_name, "f4", ("time","lat","lon",), fill_value = -9999)
    crs = dataset.createVariable('crs', 'i', ())
    #prec = dataset.createVariable('pr', "f4", ("time","y","x",))
    
    # add attributes
    times.units = 'days since 1950-01-01T00:00:00Z'
    times.calendar = cal
    times.long_name = 'time'
    times.axis = 'T'
    times.standard_name = 'time'

    lats.units = 'degrees_north'
    lats.long_name = 'latitude'
    lats.standard_name = 'latitude'
    
    lons.units = 'degrees_east'
    lons.long_name = 'longitude'
    lons.standard_name = 'longitude'

    if (param_name == 'pr'):
        var.units = 'mm'
        var.long_name = 'total daily precipitation'
        var.standard_name = 'precipitation_amount'
        dataset.title = 'daily precipitation amount'
        print('...writing pr')
        
    elif (param_name == 'tasmax'):
        var.units = 'degree_Celsius'
        var.long_name = 'daily maximum near-surface air temperature'
        var.standard_name = 'air_temperature'
        dataset.title = 'daily maximum temperature'
        print('...writing tmax')
        
    elif (param_name == 'tasmin'):
        var.units = 'degres_Celsius'
        var.long_name = 'daily minimum near-surface air temperature'
        var.standard_name = 'air_temperature'
        dataset.title = 'daily minimum temperature'
        #dataset.comment = 'Merged gridded observations of daily precipitation amount using DANUBECLIM as primary source and E-OBS (Version 16.0) data (regridded with ESMF_RegridWeightGen) as secondary source.'
        print('...writing tmin')
        
    elif (param_name == 'rsds'):
        var.units = 'W m-2'
        var.long_name = 'surface downwelling shortwave flux'
        var.standard_name = 'surface_downwelling_shortwave_flux_in_air'
        dataset.title = 'daily mean global radiation'
        print('...writing rsds') 
        
    elif (param_name == 'sfcWind'):
        var.units = 'm s-1'
        var.long_name = 'daily mean 10-m wind speed'
        var.standard_name = 'wind_speed'       
        dataset.title='daily mean 10-m wind speed'

    elif (param_name == 'hurs'):
        var.units = 'percent'
        var.long_name = 'daily mean relative humidity'
        var.standard_name = 'relative_humidity'       
        dataset.title='daily mean relative humidity'       
    
    var.grid_mapping = 'latitude_longitude'
    
    crs.grid_mapping_name = "latitude_longitude"
    crs.longitude_of_prime_meridian = 0.0 
    crs.semi_major_axis = 6378137.0
    crs.inverse_flattening = 298.257223563
    crs.comment = 'Latitude and longitude on the WGS 1984 datum'
        
    
    # write data to netCDF variable
    array3d[np.isnan(array3d)] = -9999
    var[:] = array3d
    lats[:] = lat1d
    lons[:] = lon1d

    if str(cal) == '365_day':
        d = np.arange((start_year-1950)*365, (end_year-1950+1)*365)
        dates = num2date(d, 'days since 1950-01-01T00:00:00Z', calendar=cal)                            
    elif str(cal) == '360_day':
        d = np.arange((start_year-1950)*360, (end_year-1950+1)*360)
        dates = num2date(d, 'days since 1950-01-01T00:00:00Z', calendar=cal)              
    else:
        dates = [datetime(start_year,1,1)+k*timedelta(days=1) for k in range(array3d.shape[0])]

    times[:] = date2num(dates, units=times.units, calendar=times.calendar)
    
    # global attributes
    dataset.modelname = model_name
    
    dataset.project="Climaproof, funded by the Austrian Development Agency (ADA) and co-funded by the United Nations Environmental Programme (UNEP)"
    dataset.source = "Climaproof_Downscaling Tool (Institute of Meteorology, University of Natural Resources and Life Sciences, Vienna, Austria)"
    dataset.comment = "Data downscaled from 0.1° to 0.01° resolution with xESMF Python package (based on the regridding method by Earth System Modelling Framework (ESMF))"
    dataset.conventions = "CF-1.6"
    
    dataset.close()
    
    return

def write_netcdf_obs(array3d, param_name, lat1d, lon1d, start_year, end_year, savedir, filename, cal='gregorian'):
    
#    fillval = -9999
#    array3d[np.isnan(array3d)] = fillval
    
    # create netCDF file
    savename = savedir+filename+'_'+str(start_year)+'-'+str(end_year)+'.nc'
    # check if file already exists - if yes, delete it before writing new file
    if os.path.exists(savename):
        os.remove(savename)
    
    # open new netCDF file in write mode:   
    try:
        dataset = Dataset(savename,'w',format='NETCDF4_CLASSIC')
    except(IOError):
        os.remove(savename)
        dataset = Dataset(savename,'w',format='NETCDF4_CLASSIC')
    # create dimensions
       
    dataset.createDimension("time",None)
    dataset.createDimension("lat", len(lat1d))
    dataset.createDimension("lon",len(lon1d))
    
    # create variables
    times = dataset.createVariable("time","f8",("time",))
    lats = dataset.createVariable("lat","f4",("lat",))
    lons = dataset.createVariable("lon","f4",("lon",))
    var = dataset.createVariable(param_name, "f4", ("time","lat","lon",), fill_value = -9999)
    crs = dataset.createVariable('crs', 'i', ())
    #prec = dataset.createVariable('pr', "f4", ("time","y","x",))
    
    # add attributes
    times.units = 'days since 1950-01-01T00:00:00Z'
    times.calendar = cal
    times.long_name = 'time'
    times.axis = 'T'
    times.standard_name = 'time'

    lats.units = 'degrees_north'
    lats.long_name = 'latitude'
    lats.standard_name = 'latitude'
    
    lons.units = 'degrees_east'
    lons.long_name = 'longitude'
    lons.standard_name = 'longitude'

    if (param_name == 'pr') | (param_name == 'rr'):
        var.units = 'mm'
        var.long_name = 'total daily precipitation'
        var.standard_name = 'precipitation_amount'
        dataset.title = 'daily precipitation amount'
        print('...writing pr')
        
    elif (param_name == 'tasmax') | (param_name == 'tmax'):
        var.units = 'degree_Celsius'
        var.long_name = 'daily maximum near-surface air temperature'
        var.standard_name = 'air_temperature'
        dataset.title = 'daily maximum temperature'
        print('...writing tmax')
        
    elif (param_name == 'tasmin') | (param_name == 'tmin'):
        var.units = 'degres_Celsius'
        var.long_name = 'daily minimum near-surface air temperature'
        var.standard_name = 'air_temperature'
        dataset.title = 'daily minimum temperature'
        #dataset.comment = 'Merged gridded observations of daily precipitation amount using DANUBECLIM as primary source and E-OBS (Version 16.0) data (regridded with ESMF_RegridWeightGen) as secondary source.'
        print('...writing tmin')
        
    elif (param_name == 'rsds'):
        var.units = 'W m-2'
        var.long_name = 'surface downwelling shortwave flux'
        var.standard_name = 'surface_downwelling_shortwave_flux_in_air'
        dataset.title = 'daily mean global radiation'
        print('...writing rsds') 
        
    elif (param_name == 'sfcWind'):
        var.units = 'm s-1'
        var.long_name = 'daily mean 10-m wind speed'
        var.standard_name = 'wind_speed'       
        dataset.title='daily mean 10-m wind speed'

    elif (param_name == 'hurs'):
        var.units = 'percent'
        var.long_name = 'daily mean relative humidity'
        var.standard_name = 'relative_humidity'       
        dataset.title='daily mean relative humidity'   
        
    else:
        print ('unknown parameter - edit information in function!')
        print ('aborting... no netCDF file saved!')
        dataset.close()
        os.remove(savename)
        return
    
    var.grid_mapping = 'latitude_longitude'
    
    crs.grid_mapping_name = "latitude_longitude"
    crs.longitude_of_prime_meridian = 0.0 
    crs.semi_major_axis = 6378137.0
    crs.inverse_flattening = 298.257223563
    crs.comment = 'Latitude and longitude on the WGS 1984 datum'
        
    
    # write data to netCDF variable
    array3d[np.isnan(array3d)] = -9999
    var[:] = array3d
    lats[:] = lat1d
    lons[:] = lon1d

    dates = [datetime(start_year,1,1)+k*timedelta(days=1) for k in range(array3d.shape[0])]
    times[:] = date2num(dates, units=times.units, calendar=times.calendar)
    
    # global attributes
    dataset.project="Climaproof, funded by the Austrian Development Agency (ADA) and co-funded by the United Nations Environmental Programme (UNEP)"
    dataset.source = "Climaproof Downscaling Tool (Institute of Meteorology, University of Natural Resources and Life Sciences, Vienna, Austria)"
    dataset.comment = "Data downscaled from 0.1° to 0.01° resolution with xESMF Python package (based on the regridding method by Earth System Modelling Framework (ESMF))"

    dataset.close()
    
    return

def start_tool(variable, data_type, 
               path_to_data, path_to_topo_fine, path_to_topo_coarse, path_save,
               lat_min, lat_max, lon_min, lon_max,
               start_year, end_year,
               regrid_method = 'patch'):
    
    # load data to dataset
    print('...loading data')
    ds = xr.open_dataset(path_to_data)
    topo_fine = xr.open_dataset(path_to_topo_fine)
    topo_coarse = xr.open_dataset(path_to_topo_coarse)
    
    # create a subset of the data (cut out lat/lon bos and time slice)
    print('...subsetting data')
    ds_subset = cut_domain(ds, lat_min, lat_max, lon_min, lon_max, start_year, end_year)
    topo_coarse_subset = cut_domain(topo_coarse, lat_min, lat_max, lon_min, lon_max)
    
    lat_min_fine = ds_subset['lat'].min().data
    lat_max_fine = ds_subset['lat'].max().data
    lon_min_fine = ds_subset['lon'].min().data
    lon_max_fine = ds_subset['lon'].max().data   
    
    topo_fine_subset = cut_domain(topo_fine, lat_min_fine, lat_max_fine, lon_min_fine, lon_max_fine)
    
    # regrid data
    print('...regridding data - this takes some time')
    data_regrid = regrid_data(ds_subset, topo_coarse_subset, topo_fine_subset, variable, regrid_method)
    
    # save regridded data as cf-conform netcdf file
    print('...saving data as a CF-conform netCDF file')
    path_save = path_save+'/'
    if data_type == 'model':
        # get name and calendar of the model from the original file
        model_cal, model_name = get_ncattrs(path_to_data)    
        #define the name of the new dataset
        filename = variable+'_downscaled_'+model_name
        write_netcdf(data_regrid, variable, topo_fine_subset['lat'], topo_fine_subset['lon'], start_year, end_year, path_save, filename, model_name, model_cal)
    elif data_type == 'obs':       
        filename = variable+'_observations'        
        write_netcdf_obs(data_regrid, variable, topo_fine_subset['lat'], topo_fine_subset['lon'], start_year, end_year, path_save, filename)

    data_regrid_fn = path_save+filename+'_'+str(start_year)+'-'+str(end_year)+'.nc'
    
    return data_regrid_fn, ds_subset




