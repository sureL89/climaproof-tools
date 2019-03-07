#!/usr/bin/env python

"""cmst.py: Climaproof model selection tool class for data preparation and transformation"""

__author__ = "Georg Seyerl"
__license__ = "MIT"
__maintainer__ = "Georg Seyerl"
__email__ = "georg.seyerl@gmail.com"
__status__ = "Development"

import iris
from iris.experimental.equalise_cubes import equalise_attributes

import cartopy.crs as ccrs
import os
import numpy as np
import pandas as pd

import warnings
warnings.filterwarnings("ignore")


class Cmst(object):
    """
    Class for climaproof model selection tool data preparation
    """

    def __init__(self, sel_bbox, sel_time_mean, sel_experiment, data_dir='data'):
        """
        Args:
        * sell_box (dict):
            bounding box for averaging: e.g. {"lat": np.array([32, 35]), "lon": np.array([12, 14])}
        * sel_time_mean (string):
            the temporal mean method of source dataset (e.g. summer, winter, annual)
        * sel_experiment (string):
            the experiment of source dataset (e.g. rcp26, rcp45, rcp85)
        Kwargs:
        * data_dir (path):
            directory where intermediate files will be written
        """

        self.var_selector = {
            "tasmin":"climate change signal of daily minimum near-surface air temperature",
            "tasmax":"climate change signal of daily maximum near-surface air temperature",
            "rsds":"climate change signal of daily mean surface downwelling shortwave radiation",
            "pr":"relative climate change signal of {} precipitation".format(sel_time_mean)
        }

        self.time_selector = {
            "near":0,
            "mid":1,
            "far":2
        }

        self.sel_bbox = sel_bbox
        self.sel_time_mean = sel_time_mean
        self.sel_experiment = sel_experiment
        self.data_dir = data_dir

        self.cl_ccs = iris.load_raw(
            os.path.join(data_dir,"ccs_{}_*_{}_*.nc".format(self.sel_time_mean, self.sel_experiment))
        )


    def prepare(self, cl):
        cl_ccs_mean= iris.cube.CubeList()
        ls_models = []
        realization = 0
        # Define a Cartopy 'ordinary' lat-lon coordinate reference system.
        crs_latlon = ccrs.PlateCarree()
        for i,c_ccs in enumerate(cl):
            crs_cube = c_ccs.coord_system().as_cartopy_crs()
            bbox_proj = crs_cube.transform_points(crs_latlon, self.sel_bbox['lon'], self.sel_bbox['lat'])

            x_coord = c_ccs.coords(dim_coords=True, axis='X')[0]
            y_coord = c_ccs.coords(dim_coords=True, axis='Y')[0]

            bbox_const = iris.Constraint(
                coord_values={x_coord.standard_name:lambda cell: bbox_proj[:,0][0] < cell < bbox_proj[:,0][1],
                              y_coord.standard_name:lambda cell: bbox_proj[:,1][0] < cell < bbox_proj[:,1][1]})

            c_ccs = c_ccs.extract(bbox_const)
            cl_ccs_mean.append(c_ccs.collapsed([x_coord.standard_name, y_coord.standard_name],
                                               iris.analysis.MEAN))

            # remove scalar dimensions and cell_methods (different names due to different projections)
            cl_ccs_mean[i].remove_coord(x_coord.standard_name)
            cl_ccs_mean[i].remove_coord(y_coord.standard_name)
            cl_ccs_mean[i].cell_methods = c_ccs.cell_methods

            # Add realization coordinate if it does not already exist
            if not cl_ccs_mean[i].coords('realization'):
                realization += 1
                ensemble_coord = iris.coords.AuxCoord(realization, standard_name='realization')
                cl_ccs_mean[i].add_aux_coord(ensemble_coord)

            ls_models.append(c_ccs.attributes['model'])

        return ls_models, cl_ccs_mean


    def get_pandas_df(self, sel_time_frame = "near"):
        ls_models = {}
        cl_ccs_mean = {}
        pds_ccs = {}
        pds_perc = {}
        pdf_ret = pd.DataFrame()
        for k in self.var_selector:
            ls_models[k], cl_ccs_mean[k] = self.prepare(
                self.cl_ccs.extract(
                    iris.Constraint(name=self.var_selector[k])
                )
            )
            equalise_attributes(cl_ccs_mean[k])
            cl_ccs_mean[k] = cl_ccs_mean[k].merge_cube()

            pds_ccs[k] = pd.Series(
                cl_ccs_mean[k].data[:,self.time_selector[sel_time_frame]],
                index = ls_models[k],
                name=k)

            pds_perc[k] = pd.Series(
                pds_ccs[k].rank(pct=True)*100,
                name="{}_percentiles".format(k))

            pdf_ret = pd.concat([pdf_ret, pds_ccs[k], pds_perc[k]], axis=1)

        return pdf_ret
