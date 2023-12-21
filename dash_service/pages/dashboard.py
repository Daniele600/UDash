import textwrap

import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import pandas as pd
import pandas.api.types
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import callback, dcc, html, ctx
from dash.dependencies import MATCH, Input, Output, State, ALL
from dash_service.models import Page, Project, Dashboard
import json

from dash_service.pages import get_data, is_float, is_int, years, get_geojson
from dash_service.pages import (
    add_structure,
    #get_structure_id,
    get_code_from_structure_and_dq,
    get_col_name,
    merge_with_codelist,
    get_multilang_value,
    is_string_empty,
    get_label_from_structure_and_code,
    print_exception,
    format_num
)


from flask import abort
from sqlalchemy import and_

from dash_service.components_aio.card_aio import CardAIO
from dash_service.components_aio.map_aio import MapAIO
from dash_service.components_aio.chart_aio import ChartAIO
from dash_service.components_aio.downloads_aio import DownloadsAIO
from dash_service.components_aio.heading_aio import HeadingAIO
from dash_service.components_aio.pages_navigation_aio import PagesNavigationAIO
from dash_service.components_aio.years_range_selector_aio import YearsRangeSelectorAIO

import copy
import requests

# pd.set_option("display.max_columns", None)
# pd.set_option("display.max_rows", None)
# pd.set_option("display.width", 0)

# A few constant values
ID_INDICATOR = "INDICATOR"
ID_REF_AREA = "REF_AREA"
ID_OBS_VALUE = "OBS_VALUE"
ID_DATA_SOURCE = "DATA_SOURCE"
ID_TIME_PERIOD = "TIME_PERIOD"
LABEL_COL_PREFIX = "_L_"
DEFAULT_LABELS = ["OBS_VALUE", "TIME_PERIOD", "REF_AREA"]

ELEM_ID_PAGE_NAV = "PAGE_NAV"
ELEM_ID_YEARS_RANGE_SEL = "YEARS_RANGE_SEL"
ELEM_ID_CARDS = "CARDS"
ELEM_ID_MAIN = "MAIN"
ELEM_ID_CHARTS = "CHARTS"
ELEM_ID_HEADING = "HEADING"

#CFG_N_THEMES = "THEMES"

DASHB_ELEM = "DASHB_ELEM"

#TODO Move it to config
enpoint_url = "https://sdmx.data.unicef.org/ws/public/sdmxapi/rest"


# set defaults
pio.templates.default = "plotly_white"
# px.defaults.color_continuous_scale = px.colors.sequential.BuGn
UNICEF_color_continuous_scale = [
    "#002759",
    "#00377D",
    "#0058AB",
    "#0083CF",
    "#1CABE2",
    "#69DBFF",
    "#A3EAFF",
    "#CFF4FF",
]
UNICEF_color_qualitative = [
    "#0058AB",
    "#1CABE2",
    "#00833D",
    "#80BD41",
    "#6A1E74",
    "#961A49",
    "#E2231A",
    "#F26A21",
    "#FFC20E",
    "#FFF09C",
]
# px.defaults.color_discrete_sequence = px.colors.qualitative.Dark24
px.defaults.color_discrete_sequence = UNICEF_color_qualitative
px.defaults.color_continuous_scale = UNICEF_color_continuous_scale

default_font_family = "Roboto"
default_font_size = 12


# move this elsewhere
translations = {
    "sources": {"en": "Sources", "pt": "Fontes"},
    "years": {"en": "Years", "pt": "Anos"},
    "show_historical": {"en": "Show historical data", "pt": "Mostrar série histórica"},
    "bar": {"en": "Bar", "pt": "Gráfico em colunas"},
    "line": {"en": "Line", "pt": "Gráfico em linhas"},
    "scatter": {"en": "Scatter", "pt": "Scatter PT"},
    "download_excel": {"en": "Download Excel", "pt": "Download Excel"},
    "download_csv": {"en": "Download CSV", "pt": "Download CSV"},
    "OBS_VALUE": {"en": "Value", "pt": "Valores"},
    "TIME_PERIOD": {"en": "Time period", "pt": "Ano"},
    "REF_AREA": {"en": "Geographic area", "pt": "Estado"},
}

# the configuration of the "Download plot" button in the charts
cfg_plot = {
    "toImageButtonOptions": {
        "format": "png",  # one of png, svg, jpeg, webp
        "filename": "plot",
        "width": 1200,
        "height": 800,
        "scale": 1,  # Multiply title/legend/axis/canvas sizes by this factor
    },
    "displayModeBar": True,
    "displaylogo": False,
}

colours = ["success", "warning", "danger", "info"]

EMPTY_CHART = {
    "layout": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "annotations": [
            {
                "text": "No data is available for the selected filters",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 28},
            }
        ],
    }
}


# The entry point, retrieves the page from the storage and renderes the page
def layout(lang="en", **query_params):
    """
    Returns the page layout
    """

    project_slug = query_params.get("prj", None)
    page_slug = query_params.get("page", None)

    db_config = (
        Dashboard.query.join(Project)
        .filter(and_(Page.slug == page_slug, Project.slug == project_slug))
        .first()
    )

    page_config = db_config.content
    geography = db_config.geography

    print("page_config")
    print("page_config")
    print("page_config")
    print("page_config")
    print(page_config)

    return render_page_template(
        page_config, geography, lang, query_params, project_slug
    )


# Gets the element that will be rendered on the navigation bar
def get_page_nav_items(page_config, project_slug, lang):
    nav_type = None
    ret = None
    if "page_nav" in page_config and "type" in page_config["page_nav"]:
        nav_type = page_config["page_nav"]["type"]
    if nav_type is None:
        nav_type = "all"
    if nav_type == "all":
        nav_items = (
            Dashboard.query.with_entities(
                Dashboard.slug, Dashboard.title, Project.slug.label("prj_slug")
            )
            .join(Project)
            .filter(Project.slug == project_slug)
            .all()
        )

        ret = [
            {"name": ni.title, "prj_slug": ni.prj_slug, "slug": ni.slug, "lang": lang}
            for ni in nav_items
        ]
    return ret


def render_page_template(
    page_config: dict, geojson: str, lang: str, query_params, project_slug: str
) -> html.Div:

    elem_page_nav = None
    elem_main_title = None
    #elem_years_selector = None

    nav_links = get_page_nav_items(page_config, project_slug, lang)

    if nav_links is not None and len(nav_links) > 0:
        elem_page_nav = PagesNavigationAIO(
            nav_links, query_params, aio_id=ELEM_ID_PAGE_NAV
        )

    if "main_title" in page_config:
        elem_main_title = HeadingAIO(page_config["main_title"], aio_id=ELEM_ID_HEADING)

    home_icon = None
    
    if "home_button" in page_config and "params" in page_config["home_button"]:
        #"home_button":{"params":"prj=rosa&page=home_page"},
        home_link = "?"+page_config["home_button"]["params"]
        home_icon = html.A(
            className="text-primary",
            children=html.I(className="fa-solid fa-house fa-2xl"),
            href=home_link
        )

    ret = html.Div(
        [
            dcc.Store(id="lang", data=lang),  # stores the language
            dcc.Store(id="sel_state", data=None),  # stores the selection state
            dcc.Store(id="page_config", data=page_config),  # stores the page config
            dcc.Store(id="geoj", data=geojson),  # stores the geoJson
            dcc.Store(
                id="data_structures", data={}, storage_type="session"
            ),  # stores the data structure for caching
            dcc.Location(
                id="theme"
            ),  # controls the location hash (e.g. education#theme)
            elem_page_nav,
            elem_main_title,
            html.Div(
                className="bg-light mt-2",
                children=[
                    html.Div(
                        className="d-flex justify-content-center py-2",
                        children=[dbc.ButtonGroup(id="theme_buttons")],
                    ),
                    html.Div(className="float-start align-middle ms-3", children=[home_icon]),
                ],
            ),
            html.Div(id="dashboard_contents", className="mt-2", children=[]),
        ]
    )

    return ret

def get_themes(page_config:dict):
    theme_isactive_k = [ k for k, v in page_config.items() if k.startswith('is_theme_active_')] # get all the is_theme_active_# keys
    theme_numbers = [int(n.split("_")[-1]) for n in theme_isactive_k] # get all the numbers n in is_theme_active_n
    theme_numbers = [n for n in theme_numbers if page_config["is_theme_active_"+str(n)]] # filter out the inactive themes

    ret = []
    for t in theme_numbers:
        ret.append({"id":"TH_"+str(t), "name":page_config["theme_name_"+str(t)], "components":page_config["theme_components_"+str(t)]})
    
    return ret

def get_theme_node(page_config:dict, theme_id:str):
    themes = get_themes(page_config)
    if theme_id is None:
        return themes[0]
    for t in themes:
        if t["id"]==theme_id:
            return t
    return None

def _create_card(data_struct, page_config, elem_info, lang):
    value = "-"
    label = ""
    data_source = ""
    time_period = ""
    ref_area = ""
    lbl_sources = get_multilang_value(translations["sources"], lang)
    lbl_time_period = get_multilang_value(translations["TIME_PERIOD"], lang)
    lbl_area = ""

    #it is a card, it only has one data query element
    dataquery_node = elem_info["dataquery"][0]

    if lang in translations[ID_REF_AREA]:
        lbl_area = get_multilang_value(translations["REF_AREA"], lang)
    else:
        lbl_area = get_col_name(data_struct, dataquery_node["dataflow"], ID_REF_AREA, lang)

    if is_string_empty(elem_info, "label"):
        label = get_code_from_structure_and_dq(data_struct, dataquery_node, ID_INDICATOR)[
            "name"
        ]
    else:
        label = get_multilang_value(elem_info["label"], lang)
        
    # It is a card, we just need the most recent datapoint, no labels, just the value
    try:
        df = get_data(enpoint_url,dataquery_node, lastnobservations=1, labels="id")
    # except ConnectionError as conn_err:
    except requests.exceptions.HTTPError as e:
        print_exception("Exception while downloading data for card", e)
        df = pd.DataFrame()

    if len(df) > 0:
        value = df.iloc[0][ID_OBS_VALUE]
        if "round" in elem_info and is_float(value):
            value = round(float(value), elem_info["round"])
        value = format_num(value)

        time_period = df.iloc[0][ID_TIME_PERIOD]
        ref_area = df.iloc[0][ID_REF_AREA]
        ref_area = get_code_from_structure_and_dq(       data_struct, dataquery_node, ID_REF_AREA        )["name"]
        if ID_DATA_SOURCE in df.columns:
            data_source = df.iloc[0][ID_DATA_SOURCE]

        ret = html.Div(
        # className="col",
        children=CardAIO(
            aio_id=elem_info["uid"],
            value=value,
            suffix=label,
            info_head=lbl_sources,
            info_body=data_source,
            time_period=time_period,
            area=ref_area,
            lbl_time_period=lbl_time_period,
            lbl_area=lbl_area,
        ),
    )

    return ret
    






# Trigger order: 1
# Triggered when the theme changes
# It only updates the state of the theme selection
@callback(
    Output("sel_state", "data"),
    [
        Input("theme", "hash")
    ],
    [State("page_config", "data"), State("lang", "data")],
)
def new_selection_state(theme, page_config, lang):

    themes = get_themes(page_config)
    # removes the leading # if a theme has been selected, the first theme available otherwise
    if theme:
        theme = theme[1:].upper()
    else:
        theme = str(themes[0]["id"])


    #theme = theme[1:].upper() if theme else next(iter(page_config[CFG_N_THEMES].keys()))
    # The selected years range

    selections = dict(theme=theme)

    return selections
    
# Trigger order: 2
# Triggered when the selection state changes
@callback(
    Output(HeadingAIO.ids.subtitle(ELEM_ID_HEADING), "children"),
    Output("theme_buttons", "children"),
    [
        Input("sel_state", "data"),
    ],
    State("page_config", "data"),
)
def show_themes(selections, page_config):
    
    themes = get_themes(page_config)
    # Gets the theme's name to fill the Subtitle
    #No theme selected, get the first one
    if (selections is None or selections["theme"] is None or selections["theme"].strip() == ""):
        theme_node=themes[0]
    else:
        theme_node=get_theme_node(page_config,selections["theme"])

    print("theme_node")
    print(theme_node)

    subtitle = theme_node.get("name", "")

    # Creates the Themes' buttons; hide the buttons when only one option is available
    if len(themes) == 1:
        theme_buttons = None
    else:
        theme_buttons = []
        for idx, t in enumerate(themes):
            is_active = selections["theme"] == t["id"]
            theme_buttons.append(dbc.Button(t["name"], id="btn_theme_" + t["id"], color=colours[idx%len(colours)], class_name="theme mx-1", href=f"#{t['id'].lower()}", active=is_active))

    return subtitle, theme_buttons

# Trigger order: 2 
#Downloads all the data structures needed to populate the theme
@callback(
    Output("data_structures", "data"),
    [Input("sel_state", "data")],
    [State("page_config", "data"), State("lang", "data")],
)
# Downloads all the DSD for the data.
# Typically 1 dataflow per page but can handle data from multiple Dataflows in 1 page
def download_structures(selections, page_config, lang):
    data_structures = {}

    #theme_node = page_config[CFG_N_THEMES][selections["theme"]]
    theme_node = get_theme_node(page_config, selections["theme"])

    if "components" in theme_node:
        for comp in theme_node["components"]:
            if "dataquery" in comp:
                for dq in comp["dataquery"]:
                    if "dataflow" in dq and dq["dataflow"].strip()!="":
                        add_structure(enpoint_url, data_structures, dq, lang)


    return data_structures


# Trigger order: 3
# Data structures have been downloaded -> create the elements
@callback(
    Output("dashboard_contents", "children"),
    [Input("data_structures", "data")],
    [State("sel_state", "data"), State("page_config", "data"), State("lang", "data")],
)
def create_elements(data_struct, selections, page_config, lang):
    bootstrap_cols_map = {
        "1": "col",
        "2": "col-lg-6 col-sm-12",
        "3": "col-lg-4 col-sm-12",
        "4": "col-lg-3 col-sm-12",
        "5": "col-lg-2 col-sm-6",
        "6": "col-lg-2 col-sm-6",
    }

    dashb_contents = []
    theme_node = get_theme_node(page_config, selections["theme"])

    #create a helper structure to handle the elements that will be created
    # elems_to_create = []
    elems_per_row = {}
    #divs_per_row = []
    row_keys = []
    for comp in theme_node["components"]:
        # elems_to_create.append({
        #     "row":comp["element_row"],
        #     "pos":comp["element_pos"],
        #     "cmoponent":comp,
        #     "elem_id": f'{DASHB_ELEM}_{comp["element_row"]}_{comp["element_pos"]}',
        #     #"elems_per_row": len(row["elements"]),
        # })

        if comp["element_row"] in elems_per_row:
            elems_per_row[comp["element_row"]].append(comp)
        else:
            elems_per_row[comp["element_row"]]=[comp]
        if not comp["element_row"] in row_keys:
            row_keys.append(comp["element_row"])
        row_keys.sort()
    
    #sorted(elems_to_create, key=lambda item:(item["row"],item["pos"]))

    for row_key in row_keys:
        row_elems = elems_per_row[row_key]
        bs_col = bootstrap_cols_map.get(str(len(row_elems)), "col-1")
        div_elems = []
        for row_elem in row_elems:
        #elem = html.Div(className=bs_col, children=elem)
            print("RE")
            print(row_elem)
            if row_elem["element_type"]=="card":
                elem = _create_card(data_struct, page_config, row_elem, lang)
            # elif row_elem["element_type"]=="chart":
            #     _create_chart_placeholder(data_struct, page_config, row_elem, lang)
            # elif row_elem["element_type"]=="map":
            #     _create_map_placeholder(data_struct, page_config, row_elem, lang)
            elem = html.Div(className=bs_col, children=elem)
            div_elems.append(elem)


            
            #div_elems.append(html.Div(className=bs_col, children=[html.Div(className="bg-danger w-100 min-vh-10", children=["jhg"])]))

        dashb_contents.append(
            html.Div(className="row mb-4", children=div_elems)
        )

    return dashb_contents







