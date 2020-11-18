import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import os

def li(label,href,icon):
    return  html.Li(className="nav-item", children=[
        html.A(
            className="nav-link",
            href=href, children=[
                html.I(className=f"fas fa-lg {icon}"),
                html.Span(label)
            ])
        ])

def nav_link(label, href):
    return html.A(className="collapse-item", href=href, children=label)
     

def sidebar_dropdown(label, icon, children=[]):
    sidebar_links = []
    for child in children:
        sidebar_links.append(nav_link(*child))

    return html.Li(className='nav-item', children=[
    html.A(
        className="nav-link collapsed", 
        href="#",
        **{'data-toggle':"collapse",
        'data-target':f"#{label}"},
        children=[  html.I(className=f"fas {icon}"),
                    html.Span(label) ]),
    html.Div(id=label,
        className="collapse",
        **{'data-parent':'#accordionSidebar'},
        children=[
            html.Div(
                className="bg-white py-2 collapse-inner rounded",
                children=sidebar_links)
        ])  
])

navbar = html.Ul(
    # className="navbar-nav bg-gradient-primary sidebar sidebar-dark accordion", id="accordionSidebar",children=[
    className="navbar-nav bg-primary sidebar sidebar-dark accordion", id="accordionSidebar",children=[
    # <!-- Sidebar - Brand -->
    html.A(
        className="sidebar-brand d-flex align-items-center justify-content-center", href="/",
        children=[
                html.I(className="fas fa-flask"),
                html.Span('Cond-E-L')
            ]),       
    html.Hr(className="sidebar-divider my-0"),
    li('Dashboard','/','fa-tachometer-alt'),
    li('Load','/load','fa-upload'),
    # li('Experiment','/experiment','fa-vials'),
    sidebar_dropdown('Experiment','fa-vials',children=[
        ('New','/experiment/setup'),
        ('Plots','experiment/overview'),
        ]),
    # <!-- Instruments -->
    sidebar_dropdown('Instruments','fa-digital-tachograph',children=[
        ('Furnace','/instruments/furnace'),
        ('Data Acqusition','/instruments/daq'),
        ('LCR Meter','/instruments/lcr'),
        ('Linear Stage','/instruments/stage'),
        ('Flow Controllers','/instruments/flow-controllers'),
        ]),
    # <!-- Modelling -->
    sidebar_dropdown('Modelling','fa-chart-line',children=[
        ('Conductivity','/modelling/conductivity'),
        ('Thermopower','/modelling/thermopower'),
        ('Plots','/modelling/thermopower'),
        ]),
    html.Hr(className="sidebar-divider my-0"),
    

    ])


topbar = html.Nav(
    className="navbar navbar-expand navbar-light bg-white topbar mb-4 static-top shadow",
    children=html.H3(id='topnav-title', children='Welcome to the Conductive Earth Laboratory!')
)



