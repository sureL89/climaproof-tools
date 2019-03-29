#!/usr/bin/env python

"""main.py: Climaproof model downscaling tool bokeh server application"""

__author__ = "Georg Seyerl"
__copyright__ = "Copyright 2007, The Cogent Project"
__license__ = "MIT"
__maintainer__ = "Georg Seyerl"
__email__ = "georg.seyerl@gmail.com"
__status__ = "Development"


import bokeh.plotting as bpl
import bokeh.models as bmo
import bokeh as bo
import holoviews as hv
import geoviews as gv
import geoviews.feature as gf
from cartopy import crs
import xarray as xr
import numpy as np
import json
import time
import io
import contextlib
from os.path import dirname, join


from sys import executable, argv
from subprocess import check_output
from PyQt5.QtWidgets import QFileDialog, QApplication
from downscaling_functions import start_tool

from bokeh.tile_providers import STAMEN_TONER
from bokeh.models import WMTSTileSource

tiles = {'OpenMap': WMTSTileSource(url='http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png'),
         'ESRI': WMTSTileSource(url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg'),
         'Wikipedia': WMTSTileSource(url='https://maps.wikimedia.org/osm-intl/{Z}/{X}/{Y}@2x.png'),
         'Stamen Toner': STAMEN_TONER}


# G. Seyerl 2019-03-07
# conda install -c conda-forge xesmf==0.1.1
# conda install -c conda-forge xarray==0.11.3

# Workaround to show a spinner while loading ---------------------
spinner_text = """
<!-- https://www.w3schools.com/howto/howto_css_loader.asp -->
<div class="loader">
<style scoped>
.loader {
    border: 16px solid #f3f3f3; /* Light grey */
    border-top: 16px solid #3498db; /* Blue */
    border-radius: 50%;
    width: 120px;
    height: 120px;
    animation: spin 2s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
</div>
"""

done_text = """
<div id="myDiv" class="animate-bottom">
<style scoped>
/* Add animation to "page content" */
.animate-bottom {
  position: relative;
  -webkit-animation-name: animatebottom;
  -webkit-animation-duration: 1s;
  animation-name: animatebottom;
  animation-duration: 1s
}

@-webkit-keyframes animatebottom {
  from { bottom:-100px; opacity:0 } 
  to { bottom:0px; opacity:1 }
}

@keyframes animatebottom { 
  from{ bottom:-100px; opacity:0 } 
  to{ bottom:0; opacity:1 }
}

#myDiv {
  text-align: center;
  align: left;
}
</style>
  <h1>Done</h1>
  <div>Check the visualization below</div>
</div>
"""

error_text = """
<div id="myDiv" class="animate-bottom">
<style scoped>
/* Add animation to "page content" */
.animate-bottom {
  position: relative;
  -webkit-animation-name: animatebottom;
  -webkit-animation-duration: 1s;
  animation-name: animatebottom;
  animation-duration: 1s
}

@-webkit-keyframes animatebottom {
  from { bottom:-100px; opacity:0 } 
  to { bottom:0px; opacity:1 }
}

@keyframes animatebottom { 
  from{ bottom:-100px; opacity:0 } 
  to{ bottom:0; opacity:1 }
}

#myDiv {
  text-align: center;
  align: left;
}
</style>
  <h1>ERROR</h1>
  <div>Check the output in your command line</div>
</div>
"""

input_text = """
<input type="file" id="fileUpload">
<script type="text/javascript">
function getFilePath(){
     $('input[type=file]').change(function () {
         var filePath=$('#fileUpload').val(); 
     });
}
</script>
"""


show_spinner_js = """
div_spinner.text = spinner_text
"""

def show_spinner():
    div_spinner.text = spinner_text

def hide_spinner():
    div_spinner.text = ""

# ----------------------------------------------------------------

def gui_fname(div_mod, directory='dst/data'):
    """Open a file dialog, starting in the given directory, and return
    the chosen filename"""
    # run this exact file in a separate process, and grab the result
    #file = check_output([executable, __file__, directory])
    #return file.strip()
    app = QApplication([directory])

    fname = QFileDialog.getOpenFileName(None, "Select a file...",
                                        directory, filter="All files (*)")

    div_mod.update(text=fname[0])

    return fname[0]

def gui_dirname(div_mod, directory='dst/data'):
    """Open a file dialog, starting in the given directory, and return
    the chosen filename"""
    # run this exact file in a separate process, and grab the result
    #file = check_output([executable, __file__, directory])
    #return file.strip()
    app = QApplication([directory])

    dir_name = QFileDialog.getExistingDirectory(None, "Select a file...", directory)

    div_mod.update(text=dir_name)

    return dir_name


def run_tool(event):
    try:
        data_regrid_fn, data_coarse = start_tool(inp_var.value, inp_data_type.value,
               div_src_data.text,
               div_dst_topo.text, div_src_topo.text,
               div_dir_dest.text,
               json.loads(inp_lat.value)[0], json.loads(inp_lat.value)[1],
               json.loads(inp_lon.value)[0], json.loads(inp_lon.value)[1],
               int(inp_start_year.value), int(inp_end_year.value),
               regrid_method = inp_reg_method.value)

        data_regrid = xr.open_dataset(data_regrid_fn)

        renderer = gv.renderer('bokeh')
        dataset_coarse = gv.Dataset(data_coarse['tasmax'].groupby('time.season').mean('time'), kdims=['season', 'lon', 'lat'], crs=crs.PlateCarree())
        dataset_regrid = gv.Dataset(data_regrid['tasmax'].groupby('time.season').mean('time'), kdims=['season', 'lon', 'lat'], crs=crs.PlateCarree())
        #hv.Dimension.type_formatters[np.datetime64] = '%Y-%m-%d'
        l.children[-1] = bo.layouts.row([
            renderer.get_plot(dataset_coarse.to(gv.Image, ['lon','lat']).options(width=400, colorbar=True, alpha=0.6) * gv.WMTS(tiles['Wikipedia'])).state,
            renderer.get_plot(dataset_regrid.to(gv.Image, ['lon','lat']).options(width=400, colorbar=True, alpha=0.6) * gv.WMTS(tiles['Wikipedia'])).state,
        ])

        # renderer = hv.renderer('bokeh')
        # dataset_coarse = hv.Dataset(data_coarse.tasmax.isel(time=[0]).squeeze())
        # dataset_regrid = hv.Dataset(data_regrid.tasmax.isel(time=[0]).squeeze())
        # l.children[-1] = bo.layouts.row([renderer.get_plot(dataset_coarse.to(hv.Image)).state, renderer.get_plot(dataset_regrid.to(hv.Image)).state])

        div_spinner.text = done_text
    except Exception as e:
        div_spinner.text = error_text
        print("------------- ERROR -------------")
        print(e.args)


def upd_lat_lon(attrname, old, new):
    inp_lat.value = str(bbox_countries[new]['lat'])
    inp_lon.value = str(bbox_countries[new]['lon'])

# Plots 
# %matplotlib inline
# import matplotlib.pyplot as plt
# import numpy as np
# data = xr.open_dataset(data_regrid)

# if variable == 'pr':
#     nyears = (end_year- start_year) +1
#     data_mean = data[variable].sum(dim='time')/nyears
#     data_mean_coarse = data_coarse[variable].sum(dim='time')/nyears
# else:
#     data_mean = data[variable].mean(dim='time')
#     data_mean_coarse = data_coarse[variable].mean(dim='time')

# fig, (ax1,ax2) = plt.subplots(1,2, figsize=(12,4), sharey=True)

# vmin = np.floor(np.nanmin([np.nanmin(data_mean), np.nanmin(data_mean_coarse)]))
# vmax = np.ceil(np.nanmax([np.nanmax(data_mean), np.nanmax(data_mean_coarse)]))

# data_mean_coarse.plot(ax=ax1, vmin = vmin, vmax = vmax); ax1.set_title('coarse data')
# data_mean.plot(ax=ax2, vmin = vmin, vmax = vmax); ax2.set_title('interpolated data')

# plt.figure()

# if variable == 'pr':
#     try:
#         monthly_data = data.resample(time='M').sum()
#     except(NotImplementedError):
#         dti = data.indexes['time'].to_datetimeindex()
#         data['time'] = dti
#         monthly_data = data.resample(time='M').sum()
# else:
#     try:
#         monthly_data = data.resample(time='M').mean()
#     except(NotImplementedError):
#         dti = data.indexes['time'].to_datetimeindex()
#         data['time'] = dti
#         monthly_data = data.resample(time='M').mean()
        
# monthly_data[variable].mean(dim={'lat', 'lon'}).plot()

# ----------------------------------------------------------------
#                               MAIN
# ----------------------------------------------------------------

bbox_countries = {
    "Whole Domain": {"lat":[38, 47], "lon": [13, 25]},
    "Albania": {"lat":[39.583, 42.659], "lon": [19, 21.05]},
    "Bosnia and Herzegovina": {"lat":[42.558, 45.268], "lon": [15.746, 19.671]},
    "Croatia": {"lat":[42.367, 46.527], "lon": [13.484, 19.391]},
    "Kosovo": {"lat":[41.8577, 43.2696], "lon": [20.0141, 21.7894]},
    "Macedonia": {"lat":[40.867, 42.373], "lon": [20.405, 23.033]},
    "Montenegro": {"lat":[41.864, 43.548], "lon": [18.438, 20.345]},
    "Serbia": {"lat":[41.844, 46.167], "lon": [18.859, 22.967]},
}

# Tools to show in toolbox
TOOLS = "pan,wheel_zoom,box_zoom,reset,box_select,save"

# Load description from file
div_desc = bmo.Div(text=open(join(dirname(__file__), "description.html")).read(),
               width=800)
div_hr = bmo.Div(text="<hr>", width=800)

# Create empty div for spinner
div_spinner = bmo.widgets.Div(text="",width=120,height=120)

# Create Input controls
inp_country = bmo.widgets.Select(title="Country",
                                 value = "Whole Domain",
                                 options = list(bbox_countries.keys()))
inp_lat = bmo.widgets.TextInput(title="Latitude (Format: [MIN, MAX])",
                                value = "[38, 47]" )
inp_lon = bmo.widgets.TextInput(title="Longitude (Format: [MIN, MAX])",
                                value = "[13, 25]" )
inp_start_year = bmo.widgets.TextInput(title="End year:",
                                value = "1999" )
inp_end_year = bmo.widgets.TextInput(title="Start year:",
                                value = "2010" )
inp_var = bmo.widgets.Select(title="Variable",
                             value='tasmax',
                             options=["tasmax", "tasmin", "pr", "rsds", "hurs", "sfcWind"])

inp_data_type = bmo.widgets.Select(title="Data Type:",
                                   value="obs",
                                   options=["model", "obs"])
inp_reg_method = bmo.widgets.Select(title="Regridding method:",
                             value="patch",
                             options=["patch", "bilinear"])

inp_run_tool = bmo.widgets.Button(label="Run Tool",
                                button_type="success")


inp_src_data= bmo.widgets.Button(label="Source data")
inp_src_data.on_click(lambda: gui_fname(div_src_data))
div_src_data = bmo.Div(text="", width=600)


inp_src_topo = bmo.widgets.Button(label="Source topo")
inp_src_topo.on_click(lambda: gui_fname(div_src_topo))
div_src_topo = bmo.Div(text="", width=600)

inp_dst_topo = bmo.widgets.Button(label="High res. Topo")
inp_dst_topo.on_click(lambda: gui_fname(div_dst_topo))
div_dst_topo = bmo.Div(text="", width=600)

inp_dir_dest = bmo.widgets.Button(label="Save directory")
inp_dir_dest.on_click(lambda: gui_dirname(div_dir_dest))
div_dir_dest = bmo.Div(text="", width=600)

inp_country.on_change('value', upd_lat_lon)

# Handle on click_events (unfortunately show spinner with js due to lag otherwise)
inp_run_tool.on_event(bo.events.ButtonClick, run_tool)
inp_run_tool.js_on_event(
    bo.events.ButtonClick,
    bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text),
                 code=show_spinner_js))


inputs = bo.layouts.row([
    bo.layouts.column([
        bo.layouts.row([inp_src_data, div_src_data]),
        bo.layouts.row([inp_var]),
        bo.layouts.row([inp_data_type]),
        bo.layouts.row([inp_src_topo, div_src_topo]),
        bo.layouts.row([inp_dst_topo, div_dst_topo]),
        bo.layouts.row([inp_lat, inp_lon, inp_country]),
        bo.layouts.row([inp_start_year, inp_end_year]),
        bo.layouts.row([inp_reg_method]),
        bo.layouts.row([inp_dir_dest, div_dir_dest]),
        bo.layouts.row([inp_run_tool]),
        ]),
    bo.layouts.column([
        bo.layouts.row([div_spinner]),
    ]),
])

l = bo.layouts.layout([
    bo.layouts.row([div_desc]),
    inputs,
    bo.layouts.row([div_hr]),
    bo.layouts.row(),
], sizing_mode='scale_width')

bpl.curdoc().add_root(l)
