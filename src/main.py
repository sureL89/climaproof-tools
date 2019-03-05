import bokeh.plotting as bpl
import bokeh.models as bmo
import bokeh as bo
from bokeh.palettes import Spectral6
from cmst import Cmst
import numpy as np
import json

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

div_spinner = bmo.widgets.Div(text="",width=120,height=120)
def show_spinner():
    div_spinner.text = spinner_text

def hide_spinner():
    div_spinner.text = ""
# ----------------------------------------------------------------

def get_dataset():
    bounding_box = {'lat': np.array(json.loads(inp_lat.value)),
                    'lon': np.array(json.loads(inp_lon.value))}

    cmst_upd = Cmst(bounding_box, sel_time_mean=inp_time_mean.value,
                   sel_experiment = inp_exp.value, work_dir='../data')

    pdf_ts_upd = {}
    for k in cmst_upd.time_selector:
        pdf_ts_upd[k] = bmo.ColumnDataSource(data=cmst_upd.get_pandas_df(k))

    return bmo.ColumnDataSource(data=cmst_upd.get_pandas_df('near'))

def update_plot(event):
    # src = get_dataset()
    # pdf_ts['near'].data.update(src.data)
    # hide_spinner()
    bounding_box = {'lat': np.array(json.loads(inp_lat.value)),
                    'lon': np.array(json.loads(inp_lon.value))}

    cmst_upd = Cmst(bounding_box, sel_time_mean=inp_time_mean.value,
                   sel_experiment = inp_exp.value, work_dir='../data')

    pdf_ts_upd = {}
    for k in cmst_upd.time_selector:
        pdf_ts_upd = bmo.ColumnDataSource(data=cmst_upd.get_pandas_df(k))
        pdf_ts[k].data.update(pdf_ts_upd.data)

    hide_spinner()


# ----------------------------------------------------------------
#                               MAIN
# ----------------------------------------------------------------

bounding_box = {'lat': np.array([39.6, 42.7]),
                'lon': np.array([19.3, 21.0])}

pdf_init = Cmst(bounding_box, sel_time_mean="annual",sel_experiment = 'rcp26', work_dir='../data')

hover = bmo.HoverTool(
    tooltips=[
        ('model', '@index'),
        ('tasmax', '@tasmax'),
        ('pr', '@pr')
    ]
)

TOOLS = "pan,wheel_zoom,box_zoom,reset,box_select,lasso_select, save"

columns = [
    bmo.widgets.TableColumn(field="index", title="model"),
#    bmo.widgets.TableColumn(field="tasmax", title="tasmax"),
#    bmo.widgets.TableColumn(field="pr", title="pr"),
]

# Panel 1
ls_tab = []
pdf_ts = {}
for k in pdf_init.time_selector:
    pdf_ts[k] = bmo.ColumnDataSource(data=pdf_init.get_pandas_df(k))

    # Create plot
    p = bpl.figure(tools=[TOOLS,hover],toolbar_location="left")
    p.circle(x='tasmax', y='pr',
          source = pdf_ts[k],
          size=12)

    # Horizontal line
    hline = bmo.Span(location=0, dimension='width', line_color='black', line_width=3)
    p.renderers.extend([hline])

    # Create table
    data_table = bmo.widgets.DataTable(source=pdf_ts[k], columns=columns, fit_columns=True,
                                       selectable='checkbox', width=500, height=500)

    l = bo.layouts.layout([
        bo.layouts.row([p, data_table]),
        #bo.layouts.row([data_table])
    ])

    ls_tab.append(bmo.widgets.Panel(child=l, title=k))


tabs = bmo.widgets.Tabs(tabs=ls_tab)


# Create Input controls
inp_lat = bmo.widgets.TextInput(title="Latitude (Format: [MIN, MAX])", value = "[39.6, 42.7]" )
inp_lon = bmo.widgets.TextInput(title="Longitude (Format: [MIN, MAX])", value = "[19.3, 21.0]" )
inp_time_mean = bmo.widgets.Select(title="Seasonal/Annual Mean:", value="annual", options=["annual", "summer", "winter"])
inp_exp = bmo.widgets.Select(title="Experiment:", value="rcp26", options=["rcp26", "rcp45", "rcp85"])
inp_update = bmo.widgets.Button(label="Update", button_type="success")
#x_axis = bmo.widgets.Select(title="X Axis", options=sorted(axis_map.keys()), value="Tomato Meter")
#y_axis = bmo.widgets.Select(title="Y Axis", options=sorted(axis_map.keys()), value="Number of Reviews")

inp_update.on_event(bo.events.ButtonClick, update_plot)
inp_update.js_on_event(bo.events.ButtonClick, bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text), code=show_spinner_js))

controls = [inp_lat, inp_lon, inp_time_mean, inp_exp, inp_update, div_spinner]

inputs = bo.layouts.layout([
bo.layouts.column([
        bo.layouts.row([inp_lat, inp_lon]),
        bo.layouts.row([inp_time_mean, inp_exp]),
        bo.layouts.row([inp_update])
]),
bo.layouts.column([
        bo.layouts.row([div_spinner]),
]),
])

l = bo.layouts.layout([
    bo.layouts.row([inputs]),
    bo.layouts.row([tabs]),
], sizing_mode='fixed')

bpl.curdoc().add_root(l)
