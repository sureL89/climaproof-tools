import bokeh.plotting as bpl
import bokeh.models as bmo
import bokeh as bo
from cmst import Cmst
import numpy as np
import json
from os.path import dirname, join


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
                    sel_experiment = inp_exp.value, data_dir="./data")

    return cmst_upd


def gen_upd_plot(event):
    try:
        if inp_gen_upd.label != "Update":
            cmst_upd = get_dataset()

            for k in cmst_upd.time_selector:
                pdf_ts[k] = bmo.ColumnDataSource(data=cmst_upd.get_pandas_df(k))

                # Create plot
                p[k] = bpl.figure(tools=[TOOLS,hover],toolbar_location="right")
                p[k].circle(x='tasmax', y='pr',
                            source = pdf_ts[k],
                            size=12)

                p[k].xaxis.axis_label = "climate change signal tasmax"
                p[k].yaxis.axis_label = "climate change signal pr"

                # Horizontal line
                hline = bmo.Span(location=0, dimension='width', line_color='black', line_width=3)
                vline = bmo.Span(location=0, dimension='height', line_color='black', line_width=3)
                p[k].renderers.extend([vline, hline])

                # Create table
                # Create table
                columns = [
                    bmo.widgets.TableColumn(field="index", title="model"),
                    bmo.widgets.TableColumn(field="{}".format(inp_xaxis.value), title="{}".format(inp_xaxis.value.title()), width=65),
                    bmo.widgets.TableColumn(field="{}_percentiles".format(inp_xaxis.value), title="{} Perc.".format(inp_xaxis.value.title()), width=70),
                    bmo.widgets.TableColumn(field="{}".format(inp_yaxis.value), title="{}".format(inp_yaxis.value.title()), width=65),
                    bmo.widgets.TableColumn(field="{}_percentiles".format(inp_yaxis.value), title="{} Perc.".format(inp_yaxis.value.title()), width=70),
                ]

                data_table = bmo.widgets.DataTable(source=pdf_ts[k], columns=columns, fit_columns=False,
                                                selectable='checkbox', height=p[k].plot_height, index_position=None)

                l_panel = bo.layouts.row([p[k], data_table])

                ls_tab.append(bmo.widgets.Panel(child=l_panel, title=k))

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

    # city = city_select.value
    # plot.title.text = "Weather data for " + cities[city]['title']

    # src = get_dataset(df, cities[city]['airport'], distribution_select.value)
    # source.data.update(src.data)
    ls_tab = []

    for k in pdf_ts:
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
            bmo.widgets.TableColumn(field="{}".format(inp_xaxis.value), title="{}".format(inp_xaxis.value.title()), width=65),
            bmo.widgets.TableColumn(field="{}_percentiles".format(inp_xaxis.value), title="{} Perc.".format(inp_xaxis.value.title()), width=70),
            bmo.widgets.TableColumn(field="{}".format(inp_yaxis.value), title="{}".format(inp_yaxis.value.title()), width=65),
            bmo.widgets.TableColumn(field="{}_percentiles".format(inp_yaxis.value), title="{} Perc.".format(inp_yaxis.value.title()), width=70),
        ]

        data_table = bmo.widgets.DataTable(source=pdf_ts[k], columns=columns, fit_columns=False,
                                        selectable='checkbox', height=p[k].plot_height, index_position=None)

        l_panel = bo.layouts.row([p[k], data_table])

        ls_tab.append(bmo.widgets.Panel(child=l_panel, title=k))

    tabs = bo.layouts.column([
        bo.layouts.row([inp_xaxis, inp_yaxis]),
        bo.layouts.row([bmo.widgets.Tabs(tabs=ls_tab)]),
    ])
    l.children[-1] = tabs



# ----------------------------------------------------------------
#                               MAIN
# ----------------------------------------------------------------

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
pdf_ts = {}
p = {}

tabs = bmo.widgets.Tabs(tabs=ls_tab)

# Create empty div for spinner
div_spinner = bmo.widgets.Div(text="",width=120,height=120)

# Create Input controls
inp_lat = bmo.widgets.TextInput(title="Latitude (Format: [MIN, MAX])",
                                value = "[39.6, 42.7]" )
inp_lon = bmo.widgets.TextInput(title="Longitude (Format: [MIN, MAX])",
                                value = "[19.3, 21.0]" )
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
#x_axis = bmo.widgets.Select(title="X Axis", options=sorted(axis_map.keys()), value="Tomato Meter")
#y_axis = bmo.widgets.Select(title="Y Axis", options=sorted(axis_map.keys()), value="Number of Reviews")

inp_xaxis.on_change('value', upd_axis)
inp_yaxis.on_change('value', upd_axis)

# Handle on click_events (unfortunately show spinner with js due to lag otherwise)
inp_gen_upd.on_event(bo.events.ButtonClick, gen_upd_plot)
inp_gen_upd.js_on_event(
    bo.events.ButtonClick,
    bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text),
                 code=show_spinner_js))

inputs = bo.layouts.row([
    bo.layouts.column([
        bo.layouts.row([inp_lat, inp_lon]),
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
