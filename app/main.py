#!/usr/bin/env python

"""main.py: Climaproof model selection tool bokeh server application"""

__author__ = "Georg Seyerl"
__copyright__ = "Copyright 2007, The Cogent Project"
__license__ = "MIT"
__maintainer__ = "Georg Seyerl"
__email__ = "georg.seyerl@gmail.com"
__status__ = "Development"


import bokeh.plotting as bpl
import bokeh.models as bmo
import bokeh as bo
from cmst import Cmst
import numpy as np
import json
from os.path import dirname, join

# G. Seyerl 2019-03-07

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

show_spinner_js = """
div_spinner.text = spinner_text
"""

def show_spinner():
    div_spinner.text = spinner_text

def hide_spinner():
    div_spinner.text = ""
# ----------------------------------------------------------------

def get_dataset():
    bounding_box = {'lat': np.array(json.loads(inp_lat.value)),
                    'lon': np.array(json.loads(inp_lon.value))}

    cmst_upd = Cmst(bounding_box, sel_time_mean=inp_time_mean.value,
                    sel_experiment = inp_exp.value, data_dir="/app/data")

    return cmst_upd


def gen_upd_plot(event):
    try:
        ls_tab = []
        if inp_gen_upd.label != "Update":
            cmst_upd = get_dataset()

            for k in cmst_upd.time_selector:
                pdf_ts[k] = bmo.ColumnDataSource(data=cmst_upd.get_pandas_df(k))

                # Create panel
                ls_tab.append(create_panel(k))

            tabs = bo.layouts.column([
                bo.layouts.row([inp_xaxis, inp_yaxis]),
                bo.layouts.row([bmo.widgets.Tabs(tabs=ls_tab)]),
            ])
            l.children[-1] = tabs
            inp_gen_upd.label = "Update"

        else:
            cmst_upd = get_dataset()

            pdf_ts_upd = {}
            for k in cmst_upd.time_selector:
                pdf_ts_upd = bmo.ColumnDataSource(data=cmst_upd.get_pandas_df(k))
                pdf_ts[k].data.update(pdf_ts_upd.data)

                dct_buttons[k].callback = bmo.CustomJS(args=dict(source=pdf_ts[k], filename="{}_{}_{}.csv".format(k, inp_time_mean.value, inp_exp.value)),
                                                       code=open(join(dirname(__file__), "download.js")).read())

        hide_spinner()
    except:
        div_spinner.text="""
        <div align="left" text-align="left">
        <h2>Error!</h2>
        <p text-align="left">
        Please check if your bounding box values latitude and
        longitude are within the project region
        </p>
        </div>
        """


def upd_axis(attrname, old, new):
    ls_tab = []

    for k in pdf_ts:
        # Create plot
        ls_tab.append(create_panel(k))

    tabs = bo.layouts.column([
        bo.layouts.row([inp_xaxis, inp_yaxis]),
        bo.layouts.row([bmo.widgets.Tabs(tabs=ls_tab)]),
    ])
    l.children[-1] = tabs


def create_panel(k):
    # Create plot
    p[k] = bpl.figure(tools=[TOOLS,hover],toolbar_location="right")
    p[k].circle(x=inp_xaxis.value, y=inp_yaxis.value,
                source = pdf_ts[k],
                size=12)

    p[k].xaxis.axis_label = "climate change signal {}".format(inp_xaxis.value)
    p[k].yaxis.axis_label = "climate change signal {}".format(inp_yaxis.value)

    # Horizontal line
    hline = bmo.Span(location=0, dimension='width', line_color='black', line_width=3)
    vline = bmo.Span(location=0, dimension='height', line_color='black', line_width=3)
    p[k].renderers.extend([vline, hline])

    # Create table
    columns = [
        bmo.widgets.TableColumn(field="index", title="model"),
        bmo.widgets.TableColumn(field="{}".format(inp_xaxis.value), title="{}".format(inp_xaxis.value.title()), width=65,formatter=bmo.NumberFormatter(format="0.000")),
        bmo.widgets.TableColumn(field="{}_percentiles".format(inp_xaxis.value), title="{} Perc.".format(inp_xaxis.value.title()), width=70,formatter=bmo.NumberFormatter(format="0.000")),
        bmo.widgets.TableColumn(field="{}".format(inp_yaxis.value), title="{}".format(inp_yaxis.value.title()), width=65,formatter=bmo.NumberFormatter(format="0.000")),
        bmo.widgets.TableColumn(field="{}_percentiles".format(inp_yaxis.value), title="{} Perc.".format(inp_yaxis.value.title()), width=70,formatter=bmo.NumberFormatter(format="0.000")),
    ]

    data_table = bmo.widgets.DataTable(source=pdf_ts[k], columns=columns, fit_columns=False,
                                    selectable='checkbox', height=p[k].plot_height-100, index_position=None)
    down_button = bmo.widgets.Button(label="Download CSV", button_type="primary")
    down_button.callback = bmo.CustomJS(args=dict(source=pdf_ts[k], filename="{}_{}_{}.csv".format(k, inp_time_mean.value, inp_exp.value)),
                                        code=open(join(dirname(__file__), "download.js")).read())
    dct_buttons[k] = down_button

    l_panel = bo.layouts.row([
        bo.layouts.column([p[k]]),
        bo.layouts.column([down_button, data_table]),
        ])

    panel = bmo.widgets.Panel(child=l_panel, title=k)

    return panel

def upd_lat_lon(attrname, old, new):
    inp_lat.value = str(bbox_countries[new]['lat'])
    inp_lon.value = str(bbox_countries[new]['lon'])

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
    "Slovenia": {"lat":[44.083, 46.933], "lon": [13.427, 17.467]},
}

# Tooltip when hovering over circle
hover = bmo.HoverTool(
    tooltips=[
        ('model', '@index'),
        ('tasmin', '@tasmin'),
        ('tasmax', '@tasmax'),
        ('pr', '@pr'),
        ('rsds', '@rsds')
    ]
)

# Tools to show in toolbox
TOOLS = "pan,wheel_zoom,box_zoom,reset,box_select,save"

# Load description from file
div_desc = bmo.Div(text=open(join(dirname(__file__), "description.html")).read(),
               width=800)
div_hr = bmo.Div(text="<hr>", width=800)

# Create empty panel with empty tabs
ls_tab = []
dct_buttons = {}
pdf_ts = {}
p = {}

tabs = bmo.widgets.Tabs(tabs=ls_tab)

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

inp_time_mean = bmo.widgets.Select(title="Seasonal/Annual Mean:",
                                   value="annual",
                                   options=["annual", "summer", "winter"])
inp_exp = bmo.widgets.Select(title="Experiment:",
                             value="rcp26",
                             options=["rcp26", "rcp45", "rcp85"])
inp_gen_upd= bmo.widgets.Button(label="Create Visualization",
                                button_type="success")

inp_xaxis = bmo.widgets.Select(title="X-Axis:",
                             value="tasmax",
                             options=["tasmin", "tasmax", "pr", "rsds"])
inp_yaxis = bmo.widgets.Select(title="Y-Axis:",
                             value="pr",
                             options=["tasmin", "tasmax", "pr", "rsds"])

inp_xaxis.on_change('value', upd_axis)
inp_yaxis.on_change('value', upd_axis)

inp_country.on_change('value', upd_lat_lon)

# Handle on click_events (unfortunately show spinner with js due to lag otherwise)
inp_gen_upd.on_event(bo.events.ButtonClick, gen_upd_plot)
inp_gen_upd.js_on_event(
    bo.events.ButtonClick,
    bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text),
                 code=show_spinner_js))

inputs = bo.layouts.row([
    bo.layouts.column([
        bo.layouts.row([inp_lat, inp_lon, inp_country]),
        bo.layouts.row([inp_time_mean, inp_exp]),
        bo.layouts.row([inp_gen_upd])
    ]),
    bo.layouts.column([
        bo.layouts.row([div_spinner]),
    ]),
])

l = bo.layouts.layout([
    bo.layouts.row([div_desc]),
    inputs,
    bo.layouts.row([div_hr]),
    bo.layouts.row([tabs]),
], sizing_mode='scale_width')

bpl.curdoc().add_root(l)
