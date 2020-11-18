import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import os

from app import app
from views import *
from navbar import navbar, topbar

pages = {
    '/': home.layout,
    '/load': load.layout,
    '/experiment/setup': experiment.setup,
    '/experiment/overview': experiment.overview,
    '/instruments': dashboard.layout,
    '/instruments/furnace': furnace.layout,
    '/instruments/daq': daq.layout,
    '/instruments/lcr': lcr.layout,
    '/instruments/stage': stage.layout,
    '/instruments/flow-controllers': flow_controllers.layout,
    '/modelling/conductivity': lcr.layout,
    '/modelling/thermopower': stage.layout,
    '/modelling/plots': flow_controllers.layout,
}

# data_folders = os.listdir('data')


app.layout = html.Div(id='wrapper',children=[
    dcc.Location(id='url', refresh=False),
    navbar,
    html.Div(id='content-wrapper',className="d-flex flex-column",children=[
        html.Div(id='content', children=[
            topbar,
            html.Div(id='page-content', className='container-fluid')
        ]),
    ]),

    dcc.Store(id='signal', storage_type='session'),
    ],
    )


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    # print(pages.get(pathname,'404'))
    layout = pages.get(pathname,'404')
    if callable(layout):
        return layout()
    else:
        return layout






# @app.callback(Output('page-content', 'children'),
#               [Input('url', 'pathname')])
# def display_page(pathname):
#     return pages.get(pathname,'404')

if __name__ == '__main__':
    app.run_server(
        host='0.0.0.0',
        port=9999,
        debug=True
        )