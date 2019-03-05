import bokeh.plotting as bpl
import bokeh.models as bmo
import bokeh as bo
from bokeh.palettes import Spectral6
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

    return cmst_upd

def gen_upd_plot(event):
    try:
        if inp_gen_upd.label != "Update":
            cmst_init = get_dataset()

            for k in cmst_init.time_selector:
                pdf_ts[k] = bmo.ColumnDataSource(data=cmst_init.get_pandas_df(k))

                # Create plot
                p = bpl.figure(tools=[TOOLS,hover],toolbar_location="right")
                p.circle(x='tasmax', y='pr',
                    source = pdf_ts[k],
                    size=12)

                p.xaxis.axis_label = "climate change signal tasmax"
                p.yaxis.axis_label = "climate change signal pr"

                # Horizontal line
                hline = bmo.Span(location=0, dimension='width', line_color='black', line_width=3)
                p.renderers.extend([hline])

                # Create table
                data_table = bmo.widgets.DataTable(source=pdf_ts[k], columns=columns, fit_columns=False,
                                                selectable='checkbox', height=p.plot_height, index_position=None)

                l_panel = bo.layouts.row([p, data_table])

                ls_tab.append(bmo.widgets.Panel(child=l_panel, title=k))

            tabs = bmo.widgets.Tabs(tabs=ls_tab)
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
        <p text-align="left">Please check if your bounding box values latitude and longitude are within the project region</p>
        </div>
        """



# ----------------------------------------------------------------
#                               MAIN
# ----------------------------------------------------------------

# bounding_box = {'lat': np.array([39.6, 42.7]),
#                 'lon': np.array([19.3, 21.0])}

#pdf_init = Cmst(bounding_box, sel_time_mean="annual",sel_experiment = 'rcp26', work_dir='../data')

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
    bmo.widgets.TableColumn(field="pr_percentiles", title="pr Percentile", width=70),
    bmo.widgets.TableColumn(field="tasmin_percentiles", title="Tmin Perc.", width=65),
    bmo.widgets.TableColumn(field="tasmax_percentiles", title="Tmax Perc.", width=65),
    bmo.widgets.TableColumn(field="rsds_percentiles", title="Rsds Perc.", width=65),
#    bmo.widgets.TableColumn(field="tasmax", title="tasmax"),
#    bmo.widgets.TableColumn(field="pr", title="pr"),
]

desc = bmo.Div(text=open(join(dirname(__file__), "description.html")).read(), width=800)

# Create empty panel with empty tabs
ls_tab = []
pdf_ts = {}

tabs = bmo.widgets.Tabs(tabs=ls_tab)


# Create Input controls
inp_lat = bmo.widgets.TextInput(title="Latitude (Format: [MIN, MAX])", value = "[39.6, 42.7]" )
inp_lon = bmo.widgets.TextInput(title="Longitude (Format: [MIN, MAX])", value = "[19.3, 21.0]" )
inp_time_mean = bmo.widgets.Select(title="Seasonal/Annual Mean:", value="annual", options=["annual", "summer", "winter"])
inp_exp = bmo.widgets.Select(title="Experiment:", value="rcp26", options=["rcp26", "rcp45", "rcp85"])
inp_gen_upd= bmo.widgets.Button(label="Create Visualization", button_type="success")
#x_axis = bmo.widgets.Select(title="X Axis", options=sorted(axis_map.keys()), value="Tomato Meter")
#y_axis = bmo.widgets.Select(title="Y Axis", options=sorted(axis_map.keys()), value="Number of Reviews")

# Handle on click_events (unfortunately show spinner with js due to lag otherwise)
inp_gen_upd.on_event(bo.events.ButtonClick, gen_upd_plot)
inp_gen_upd.js_on_event(bo.events.ButtonClick, bmo.CustomJS(args=dict(div_spinner=div_spinner, spinner_text=spinner_text), code=show_spinner_js))

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
    bo.layouts.row([desc]),
    inputs,
    bo.layouts.row([tabs]),
], sizing_mode='scale_width')

bpl.curdoc().add_root(l)
