#!/usr/bin/env python

"""main.py: Climaproof model downscaling tool bokeh server application"""

__author__ = "Georg Seyerl"
__copyright__ = "Copyright 2017"
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
import os

DOCKER_CONTAINER = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
if not DOCKER_CONTAINER == "True":
    from PyQt5.QtWidgets import QFileDialog, QApplication

from downscaling_functions import start_tool

from bokeh.tile_providers import STAMEN_TONER
from bokeh.models import WMTSTileSource

tiles = {'OpenMap': WMTSTileSource(url='http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png'),
         'ESRI': WMTSTileSource(url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg'),
         'Wikipedia': WMTSTileSource(url='https://maps.wikimedia.org/osm-intl/{Z}/{X}/{Y}@2x.png'),
         'Stamen Toner': STAMEN_TONER}

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

show_spinner_js = """
div_spinner.text = spinner_text
"""

def show_spinner():
    div_spinner.text = spinner_text

def hide_spinner():
    div_spinner.text = ""

# ----------------------------------------------------------------

# Workaround for file upload ---------------------

IMPL = """
import * as p from "core/properties"
import {LayoutDOM, LayoutDOMView} from "models/layouts/layout_dom"

export class FileInputView extends LayoutDOMView
  initialize: (options) ->
    super(options)
    input = document.createElement("input")
    input.type = "file"
    input.onchange = () =>
      @model.value = input.value
    @el.appendChild(input)

export class FileInput extends LayoutDOM
  default_view: FileInputView
  type: "FileInput"
  @define {
    value: [ p.String ]
  }
"""

class FileInput(bmo.LayoutDOM):
    __implementation__ = IMPL
    value = bo.core.properties.String()

def gui_fname(div_mod, directory='data'):
    """Open a file dialog, starting in the given directory, and return
    the chosen filename"""
    app = QApplication([directory])

    fname = QFileDialog.getOpenFileName(None, "Select a file...",
                                        directory, filter="All files (*)")

    div_mod.update(text=fname[0])

    return fname[0]

def gui_dirname(div_mod, directory='data'):
    """Open a file dialog, starting in the given directory, and return
    the chosen filename"""
    app = QApplication([directory])

    dir_name = QFileDialog.getExistingDirectory(None, "Select a file...", directory)

    div_mod.update(text=dir_name)

    return dir_name

# ----------------------------------------------------------------

def run_tool(event):
    try:
        if DOCKER_CONTAINER == "True":
            if not os.path.exists(os.path.join('/data', 'outp')):
                os.makedirs(os.path.join('/data', 'outp'))

            data_regrid_fn, data_coarse = start_tool(inp_var.value, inp_data_type.value,
                                                     os.path.join('/data', div_src_data.value.rsplit('\\',1)[-1]),
                                                     os.path.join('/data', div_dst_topo.value.rsplit('\\',1)[-1]),
                                                     os.path.join('/data', div_src_topo.value.rsplit('\\',1)[-1]),
                                                     os.path.join('/data', 'outp'),
                                                     json.loads(inp_lat.value)[0], json.loads(inp_lat.value)[1],
                                                     json.loads(inp_lon.value)[0], json.loads(inp_lon.value)[1],
                                                     int(inp_start_year.value), int(inp_end_year.value),
                                                     regrid_method = inp_reg_method.value)
        else:
            data_regrid_fn, data_coarse = start_tool(inp_var.value, inp_data_type.value,
                div_src_data.text,
                div_dst_topo.text, div_src_topo.text,
                div_dir_dest.text,
                json.loads(inp_lat.value)[0], json.loads(inp_lat.value)[1],
                json.loads(inp_lon.value)[0], json.loads(inp_lon.value)[1],
                int(inp_start_year.value), int(inp_end_year.value),
                regrid_method = inp_reg_method.value)

        data_regrid = xr.open_dataset(data_regrid_fn)

        # Plot
        renderer = gv.renderer('bokeh')
        dataset_coarse = gv.Dataset(data_coarse[inp_var.value].groupby('time.season').mean('time'),
                                    kdims=['season', 'lon', 'lat'],
                                    crs=crs.PlateCarree())
        dataset_regrid = gv.Dataset(data_regrid[inp_var.value].groupby('time.season').mean('time'),
                                    kdims=['season', 'lon', 'lat'],
                                    crs=crs.PlateCarree())

        gv_plot = renderer.get_plot(
            (dataset_coarse.to(gv.Image, ['lon','lat']).options(width=350, colorbar=True, alpha=0.6, title="Coarse data") * gv.WMTS(tiles['Wikipedia'])) + \
            (dataset_regrid.to(gv.Image, ['lon','lat']).options(width=350, colorbar=True, alpha=0.6, title="Downscaled data") * gv.WMTS(tiles['Wikipedia']))
        )

        inp_sel_season = bmo.widgets.Select(title="Season:",
                                value="DJF",
                                options=["DJF","JJA","MAM","SON"])
        inp_sel_season.on_change('value', lambda attrname, old, new: gv_plot.update((new,)))
        l.children[-1] = bo.layouts.layout(bo.layouts.row([inp_sel_season]),
                                            bo.layouts.row([gv_plot.state]))

        div_spinner.text = done_text
    except Exception as e:
        div_spinner.text = error_text
        print("------------- ERROR -------------")
        print(e.args)


def upd_lat_lon(attrname, old, new):
    inp_lat.value = str(bbox_countries[new]['lat'])
    inp_lon.value = str(bbox_countries[new]['lon'])

def file_inputs(attrname, old, new):
    import pdb; pdb.set_trace()
    pass




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
div_desc = bmo.Div(text=open(os.path.join(os.path.dirname(__file__), "description.html")).read(),
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
inp_var = bmo.widgets.Select(title="Variable:",
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


inp_country.on_change('value', upd_lat_lon)


# Handle on click_events (unfortunately show spinner with js due to lag otherwise)
inp_run_tool.on_event(bo.events.ButtonClick, run_tool)
inp_run_tool.js_on_event(
    bo.events.ButtonClick,
    bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text),
                 code=show_spinner_js))


if DOCKER_CONTAINER == "True":
    inp_src_data = bmo.Div(text="Source data:", width=100)
    # div_src_data = FileInput()
    # div_src_data = bmo.Div(text="""<input id="src_data" type="file">""")
    div_src_data = bmo.widgets.TextInput(value="/tmp")
    # div_src_data.on_change('value', file_inputs)

    inp_src_topo = bmo.Div(text="Source topo", width=100)
    # div_src_topo = FileInput()
    #div_src_topo = bmo.Div(text="""<input id="src_topo" type="file">""")
    div_src_topo = bmo.widgets.TextInput(value="/tmp")

    inp_dst_topo = bmo.Div(text="High res. Topo", width=100)
    # div_dst_topo = FileInput()
    #div_dst_topo = bmo.Div(text="""<input id="dst_topo" type="file">""")
    div_dst_topo = bmo.widgets.TextInput(value="/tmp")

    inp_dir_dest = bmo.Div(text="", width=100)
    div_dir_dest = bmo.Div(text="", width=600)
else:
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
