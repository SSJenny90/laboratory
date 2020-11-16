import dash_html_components as html
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
from app import app, lab
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
table_columns = [{
            'id': 'target_temp',
            'name': 'Target [\u00B0C]',
            'type': 'numeric'
        }, {
            'id': 'hold_length',
            'name': 'Hold Length [hrs]',
            'type': 'numeric',
        }, {
            'id': 'heat_rate',
            'name': 'Heating Rate',
            'type': 'numeric',
        }, {
            'id': 'interval',
            'name': 'Interval [minutes]',
            'type': 'numeric',
        }, {
            'id': 'buffer',
            'name': 'fo2 buffer',
            'type': 'text',
            'presentation': 'dropdown'
        }, {
            'id': 'offset',
            'name': 'fo2 offset [log Pa]',
            'type': 'numeric',
        }, {
            'id': 'fo2_gas',
            'name': 'Gas mix type',
            'type': 'text',
            'presentation': 'dropdown'
        }, {
            'id': 'thermopower',
            'name': 'Target gradient',
            'type': 'numeric',
        }]

table = dash_table.DataTable(
    id='setup-table',
    editable=True,
    data=[{x['id']:None for x in table_columns}],
    columns=table_columns,
    dropdown={
        'buffer': {
                'options': [
                    {'label': 'a', 'value': 'A'},
                ]
            },
            'fo2_gas': {
                 'options': [
                    {'label': 'CO2/H2', 'value': 'h2'},
                    {'label': 'CO2/CO', 'value': 'co'},
                ]
            }
        }
)


fig = make_subplots(specs=[[{"secondary_y": True}]])
# Add traces
fig.add_trace(
    go.Scatter(x=[], y=[], name="temp"),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(x=[], y=[], name="fo2",line_shape='vh'),
    secondary_y=True,
    
)

fig.update_layout(
    showlegend=False,
    yaxis=dict(
        title="Temperature",
        titlefont=dict(
            color="#1f77b4"
        ),
        tickfont=dict(
            color="#1f77b4"
        )
    ),
    yaxis2=dict(
        title="fo2 [log Pa]",
        titlefont=dict(
            color="#d62728"
        ),
        tickfont=dict(
            color="#d62728"
        ),
        anchor="x",
        overlaying="y",
        side="right"
    ),
)

layout = html.Div(id='setup',
    className='container', 
    children = [
    html.H1(children='Setup', className='text-center'),
    table, 
    html.Button('Add Row', id='add-rows-button', className='my-3 btn btn-primary', n_clicks=0),
    dcc.Graph(figure=fig, id='setup-fig',
        className='w-100')

])


#     dcc.Graph(id='adding-rows-graph')
# ])


@app.callback(
    Output('setup-table', 'data'),
    [Input('add-rows-button', 'n_clicks')],
    [State('setup-table', 'data'),
     State('setup-table', 'columns')])
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append(rows[-1])
    return rows



@app.callback(
    Output('setup-fig', 'figure'),
    [Input('setup-table', 'data'),
     Input('setup-table', 'columns'),
     State('setup-fig','figure')])
def display_output(rows, columns, figure):
    rows.insert(0,{k:0 for k in rows[0].keys()})
    df = pd.DataFrame(rows)

    hours = df.hold_length
    ind = df.thermopower.notnull()
    hours.loc[ind] = hours.loc[ind] + 4

    hours = hours + (df.target_temp - df.target_temp.shift()) / df.heat_rate / 60
    hours[0] = 0

    hours = pd.to_timedelta(hours.cumsum(),'h')
    
    # df.loc[df.thermopower.notnull(),'thermo_time'] = 4 #add 4 hours per every thermopwoer measurements
    # df.loc[0,'thermo_time'] = 0 #set first row back to 
    # thermo_time = pd.to_timedelta(df['hold_length'].cumsum(),'h')

    # pd.to_timedelta(df['hold_length'].cumsum(),'h')
    x = datetime.now() + hours

    figure['data'][0]['x'] = x
    figure['data'][0]['y'] = df['target_temp']

    figure['data'][1]['x'] = x
    figure['data'][1]['y'] = df['offset']
    return figure