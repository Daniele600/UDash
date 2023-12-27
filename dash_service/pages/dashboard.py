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

from dash_service.pages import (
    get_data, is_float, is_int, years, get_geojson,get_data_with_labels,
    add_structure,
    #get_structure_id,
    get_code_from_structure_and_dq,
    get_col_name,
    merge_with_codelist,
    get_multilang_value,
    is_string_empty,
    get_label_from_structure_and_code,
    print_exception,
    format_num,
    round_pandas_col
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
endpoint_url = "https://sdmx.data.unicef.org/ws/public/sdmxapi/rest"
CHART_TYPE_NODE_PREFIX = "chart_type_"
CFG_TIME_PERIOD_START = "year_start"
CFG_TIME_PERIOD_END = "year_end"


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

def get_element_by_uid(page_config:dict, uid:str):
    themes = get_themes(page_config)
    for t in themes:
        for comp in t["components"]:
            if comp["uid"]==uid:
                return comp
    return None



# loops the data node and returns the options for the dropdownlists: options + default value
def get_ddl_values(data_node, data_structures, column_id, lang):
    items = []
    default_item = ""
    for idx, data_cfg in enumerate(data_node):
        # is it there a label? Override the one read from the data
        if not is_string_empty(data_cfg):
            lbl = get_multilang_value(data_cfg["label"], lang)
        elif "multi_indicator" in data_cfg:
            labels = []
            for multi_cfg in data_cfg["multi_indicator"]:
                tmp_lbl = get_code_from_structure_and_dq(
                    data_structures, multi_cfg, column_id
                )["name"]
                labels.append(tmp_lbl)
            lbl = " - ".join(labels)

        else:
            lbl = get_code_from_structure_and_dq(data_structures, data_cfg, column_id)[
                "name"
            ]

        items.append({"label": lbl, "value": str(idx)})
        if idx == 0:
            default_item = str(idx)
    return items, default_item




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
        df = get_data(endpoint_url,dataquery_node, lastnobservations=1, labels="id")
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

def _create_chart_placeholder(data_struct, page_config, elem_info, lang):
    #elem = elem_info["elem"]
    title = elem_info.get("label", "")
    # The dropdownlist elements
    ddl_items, default_item = get_ddl_values(
        elem_info["dataquery"], data_struct, ID_INDICATOR, lang
    )
    #chart_types = [{"label":get_multilang_value(translations[t], lang), "value":t} for t in elem_info["chart_type"] if elem_info["chart_type"]]
    chart_types = [k for k in elem_info.keys() if k.startswith(CHART_TYPE_NODE_PREFIX)]
    chart_types = [k for k in chart_types if elem_info[k]["is_active"]]
    chart_types = [k[len(CHART_TYPE_NODE_PREFIX):] for k in chart_types]
    chart_types = [{"label":get_multilang_value(translations[t], lang), "value":t} for t in chart_types]
    
    default_graph = chart_types[0]["value"]

    ret = ChartAIO(
        aio_id=elem_info["uid"],
        title=title,
        plot_cfg=cfg_plot,
        info_title=get_multilang_value(translations["sources"], lang),
        lbl_excel=get_multilang_value(translations["download_excel"], lang),
        lbl_csv=get_multilang_value(translations["download_csv"], lang),
        dropdownlist_options=ddl_items,
        dropdownlist_value=default_item,
        chart_types=chart_types,
        default_graph=default_graph,
    )

    return html.Div(children=ret)

def _create_map_placeholder(data_struct, page_config, elem_info, lang):
    title = elem_info.get("label", "")
    ddl_items, default_item = get_ddl_values(
        elem_info["dataquery"], data_struct, ID_INDICATOR, lang
    )

    ret = MapAIO(
        aio_id=elem_info["uid"],
        title=title,
        plot_cfg=cfg_plot,
        info_title=get_multilang_value(translations["sources"], lang),
        lbl_show_hist=get_multilang_value(translations["show_historical"], lang),
        lbl_excel=get_multilang_value(translations["download_excel"], lang),
        lbl_csv=get_multilang_value(translations["download_csv"], lang),
        dropdownlist_options=ddl_items,
        dropdownlist_value=default_item,
    )

    return html.Div(children=ret)
    






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
                        add_structure(endpoint_url, data_structures, dq, lang)


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

        if comp["element_row"] in elems_per_row:
            elems_per_row[comp["element_row"]].append(comp)
        else:
            elems_per_row[comp["element_row"]]=[comp]
        if not comp["element_row"] in row_keys:
            row_keys.append(comp["element_row"])
        row_keys.sort()

    for row_key in row_keys:
        row_elems = elems_per_row[row_key]
        bs_col = bootstrap_cols_map.get(str(len(row_elems)), "col-1")
        div_elems = []
        for row_elem in row_elems:
            elem = None
            if row_elem["element_type"]=="card":
                elem = _create_card(data_struct, page_config, row_elem, lang)
            elif row_elem["element_type"]=="chart":
                elem = _create_chart_placeholder(data_struct, page_config, row_elem, lang)
            elif row_elem["element_type"]=="map":
                elem = _create_map_placeholder(data_struct, page_config, row_elem, lang)


            div_elems.append(html.Div(className=bs_col, children=elem))
        
        dashb_contents.append(
            html.Div(className="row mb-4", children=div_elems)
        )

    return dashb_contents






# Trigger order: 4
# Triggered when the selection changes. Updates the charts.
@callback(
    Output(ChartAIO.ids.chart(MATCH), "figure"),
    Output(ChartAIO.ids.info_text(MATCH), "children"),
    Output(ChartAIO.ids.info_icon(MATCH), "style"),
    Output(ChartAIO.ids.missing_areas(MATCH), "children"),
    Output(ChartAIO.ids.download_api_call(MATCH), "value"),
    [
        Input(ChartAIO.ids.ddl(MATCH), "value"),
        Input(ChartAIO.ids.chart_types(MATCH), "value"),
    ],
    [
        State("data_structures", "data"),
        State("sel_state", "data"),
        State("page_config", "data"),
        State(ChartAIO.ids.card_title(MATCH), "id"),
        State("lang", "data"),
    ],
)
def update_charts(
    ddl_value, chart_type, data_structures, selections, page_config:dict, component_id, lang
):
    
    #selected_theme = get_theme_node(page_config,selections["theme"])
    print("component_id")
    print(component_id)
    print("Chart tye")
    print(chart_type)
    #Find the element in the configuration having the matching uid
    updated_elem = get_element_by_uid(page_config,component_id["aio_id"])
    print(updated_elem)
    # find the data node in the configuration for the user's selection
    data_cfg = updated_elem["dataquery"][int(ddl_value)]

    #Start creating the data
    df = pd.DataFrame()

    # indicator_name = ""
    # indic_labels = {}
    api_call = {"component_id": component_id, "calls": []}

    time_period = [page_config.get(CFG_TIME_PERIOD_START,1900),page_config.get(CFG_TIME_PERIOD_END,None)]


    lastnobservations = None
    if chart_type == "line":
        lastnobservations = None
    else:
        lastnobservations = 1

    print(endpoint_url, data_cfg, time_period,lastnobservations)

    try:
        # df = get_data(endpoint_url,
        #     data_cfg, years=time_period, lastnobservations=lastnobservations
        # )
        df = get_data_with_labels(endpoint_url, data_cfg, data_structures, cols_to_get_labels=[ID_REF_AREA, ID_DATA_SOURCE], years=time_period, lastnobservations=lastnobservations)
        # api_call["calls"].append(
        #     {
        #         "cfg": data_cfg,
        #         "years": time_period,
        #         "lastnobservations": lastnobservations,
        #     }
        # )
    except requests.exceptions.HTTPError as e:
        print_exception("Exception while downloading data for charts", e)
        df = pd.DataFrame()

    if df.empty:
        return EMPTY_CHART, ""

    if len(df) > 0 and "round" in data_cfg and data_cfg["round"]is not None and data_cfg["round"]!="noRound":
        df = round_pandas_col(df, ID_OBS_VALUE, data_cfg["round"])

    indicator_name = get_code_from_structure_and_dq(
        data_structures, data_cfg, ID_INDICATOR
    )["name"]

    df[ID_OBS_VALUE] = pd.to_numeric(df[ID_OBS_VALUE], errors="coerce")
    df[ID_TIME_PERIOD] = pd.to_numeric(df[ID_TIME_PERIOD], errors="coerce")

    # The source icon and information
    source = ""
    display_source = {"display": "none"}
    if LABEL_COL_PREFIX + ID_DATA_SOURCE in df.columns:
        source = ", ".join(list(df[LABEL_COL_PREFIX + ID_DATA_SOURCE].unique()))
    if source != "":
        display_source = {"display": "visible"}

    # The missing areas:
    missing_areas = ""
    if "force_ref_areas" in data_cfg:
        areas_to_force = data_cfg["force_ref_areas"] # e.g. "AFG+BGD+BTN+IND+MDV+NPL+PAK+LKA"
        areas_to_force = areas_to_force.split("+")
        existing_ref_areas = list(df[ID_REF_AREA].unique())

        miss = [a for a in areas_to_force if a not in existing_ref_areas]
        miss = [
            get_label_from_structure_and_code(
                data_structures, data_cfg["dataflow"], ID_REF_AREA, a
            )
            for a in miss
        ]
        if len(miss) > 0:
            missing_areas = "No data for: " + ", ".join(miss)

    # set the chart title, wrap the text when the indicator name is too long
    chart_title = textwrap.wrap(
        indicator_name,
        width=55,
    )
    chart_title = "<br>".join(chart_title)

    #Build the chart's options
    chart_options_static = {
        "bar":{"barmode":"group"},
        "line":{"line_shape":"spline", "render_mode":"svg"}
    }
    chart_options = chart_options_static[chart_type]
    chart_options["color_discrete_sequence"] = UNICEF_color_qualitative
    for opt_k, opt_val in updated_elem[CHART_TYPE_NODE_PREFIX + chart_type].items():
        chart_options[opt_k]=opt_val
    
    chart_options_xaxis = {"categoryorder": "total descending"}
    if chart_type == "line":
        chart_options_xaxis["tickformat"] = "d"

    # set the layout to center the chart title and change its font size and color
    layout = go.Layout(
        title=chart_title,
        title_x=0.5,
        font=dict(family=default_font_family, size=default_font_size),
        legend=dict(x=0.9, y=0.5),
        xaxis=chart_options_xaxis,
        modebar={"orientation": "v"},
    )

    fig = getattr(px, chart_type)(df, **chart_options)
    fig.update_layout(layout)
    
    return fig, source, display_source, missing_areas, json.dumps(api_call)





# Data download (Excel)
@callback(
    Output(DownloadsAIO.ids.dcc_down_excel(MATCH), "data"),
    [
        Input(DownloadsAIO.ids.btn_down_excel(ALL), "n_clicks"),
    ],
    [
        State(ChartAIO.ids.download_api_call(ALL), "value"),
        State(MapAIO.ids.download_api_call(ALL), "value"),
        State("page_config", "data"),
        State("sel_state", "data"),
    ],
    prevent_initial_call=True,
)
# Downloads the DSD for the data.
def download_excel(n_clicks, chart_api_call, map_api_call,page_config, selections):
    #theme = get_theme_node(page_config,selections["theme"])
    updated_elem = get_element_by_uid(page_config,ctx.triggered_id["aio_id"])

    print("ctx.triggered_id")
    print(ctx.triggered_id)
    print("chart_api_call")
    print(chart_api_call,)
    print("map_api_call")
    print(map_api_call)


    # triggered_cfg = _find_triggerer(ctx.triggered_id, chart_api_call, map_api_call)
    # df = _get_data_for_download(triggered_cfg,page_config)
    df = pd.DataFrame({"A":"a"})
    # return dcc.send_data_frame(df.to_excel, "data.xlsx", index=False)