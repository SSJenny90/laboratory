import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from app import app
from views import *


pages = {
    '/': home.layout,
    '/setup': setup.layout,
    '/instruments': dashboard.layout,
    '/instruments/furnace': furnace.layout,
    '/instruments/daq': daq.layout,
    '/instruments/lcr': lcr.layout,
    '/instruments/stage': stage.layout,
    '/instruments/flow-controllers': flow_controllers.layout,
}

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(id='navbar',
        children=[
            dbc.NavItem(dbc.NavLink("Setup", href="/setup")),
            dbc.NavItem(dbc.NavLink("Experiment", href="/experiment")),
            dbc.NavItem(dbc.NavLink("Experiment", href="/experiment")),
  
            dbc.DropdownMenu(label="Instruments",
                children=[
                    dbc.DropdownMenuItem("Dashboard", href="/instruments"),
                    html.Div(className='dropdown-divider'),
                    dbc.DropdownMenuItem("Furnace", href="/instruments/furnace"),
                    dbc.DropdownMenuItem("LCR Meter", href="/instruments/lcr"),
                    dbc.DropdownMenuItem("DAQ", href="/instruments/daq"),
                    dbc.DropdownMenuItem("Flow Controllers", href="/instruments/flow-controllers"),
                    dbc.DropdownMenuItem("Stage", href="/instruments/stage"),
                ],
                nav=True,
                in_navbar=True,
            ),
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Setup", header=True),
                    dbc.DropdownMenuItem("Page 2", href="#"),
                    dbc.DropdownMenuItem("Page 3", href="#"),
                ],
                nav=True,
                in_navbar=True,
                label="More",
            ),
        ],
    brand="CondEL",
    brand_href="/",
    color="primary",
    dark=True,
    ),
    html.Div(id='page-content',className='container-fluid')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    return pages.get(pathname,'404')


if __name__ == '__main__':
    app.run_server(
        host='0.0.0.0',
        port=9999,
        debug=True
        )