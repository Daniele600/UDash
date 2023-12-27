import json
import pathlib
from USDMX import sdmx_data_access
from datetime import datetime
from dash import html
import pandas as pd

from ..app_settings import FILES_UPLOAD_PATH

years = list(range(2007, datetime.now().year))


def page_not_found(pathname):
    return html.P("No page '{}'".format(pathname))


# def get_data(cfg_data, years=None, countries=[], last_n_obs=False, labels="id"):
def get_structure(data_endpoint_url,cfg_data, lang):
    api_access = sdmx_data_access.SDMX_DataAccess(data_endpoint_url)

    splitted = cfg_data.split(",")
    ret = api_access.get_dataflow_info(splitted[0],splitted[1],splitted[2],lang)

    return ret

def get_data(data_endpoint_url,cfg_data, years=None, lastnobservations=None, labels="id"):
    api_access = sdmx_data_access.SDMX_DataAccess(data_endpoint_url)

    startperiod = None
    endperiod = None
    

    if years is not None:
        startperiod = years[0]
        endperiod = years[1]

    # if "startperiod" in cfg_data:
    #     startperiod = cfg_data["startperiod"]
    # if "endperiod" in cfg_data:
    #     endperiod = cfg_data["endperiod"]
    dataflow_id_split = cfg_data["dataflow"].split(",")

    df = api_access.get_data(
        dataflow_id_split[0],dataflow_id_split[1],dataflow_id_split[2],
        dq=cfg_data["dq"],
        lastnobs=lastnobservations,
        startperiod=startperiod,
        endperiod=endperiod,
        labels=labels,
    )

    return df

def get_data_with_labels(data_endpoint_url,cfg_data, data_structures, cols_to_get_labels = None, years=None, lastnobservations=None, labels="id"):
    df = get_data(data_endpoint_url,cfg_data, years=None, lastnobservations=None, labels="id")
    # Assign labels to codes
    if cols_to_get_labels is None:
        cols_to_get_labels = df.columns
    for col in cols_to_get_labels:
        df = merge_with_codelist(df, data_structures, cfg_data["dataflow"], col)
    return df


# Get geoJson
def get_geojson(geoj_filename: str):
    geojson_path =f"./dash_service/{FILES_UPLOAD_PATH}/{geoj_filename}"
    
    with open(geojson_path) as shapes_file:
        geo_json_data = json.load(shapes_file)
    return geo_json_data


"""
SDMX structure and data utils
"""

# composes the structure id as agency|id|version
# def get_structure_id(data_node):
#     return f"{data_node['agency']}|{data_node['id']}|{data_node['version']}"


# Downloads and adds the structure to the struct object if it doesn't exist, skips otherwise
def add_structure(data_endpoint_url, structs, data_cfg, lang):
    #struct_id = get_structure_id(data_cfg)

    if not data_cfg["dataflow"] in structs:
        # print("GETTING " + struct_id)
        structs[data_cfg["dataflow"]] = get_structure(data_endpoint_url,data_cfg["dataflow"], lang)
    # else:
    # print(">>SKIPPED " + struct_id)


# returns the codelist attached to a dataflow's column (dimension or attribute)
# def _get_dim_or_attrib_from_struct(struct_id, dim_or_attrib_id, structs):
def _get_dim_or_attrib_from_struct(structs, struct_id, dim_or_attrib_id):
    cl = next(
        (
            dim
            for dim in structs[struct_id]["dsd"]["dims"]
            if dim["id"] == dim_or_attrib_id
        ),
        None,
    )
    if cl is None:
        cl = next(
            (
                dim
                for dim in structs[struct_id]["dsd"]["attribs"]
                if dim["id"] == dim_or_attrib_id
            ),
            None,
        )

    return cl


def get_col_name(
    data_structures,
    struct_id,
    dim_or_attrib_id,
    lang="en",
    lbl_override=None,
):
    if (
        lbl_override is not None
        and dim_or_attrib_id in lbl_override
        and lang in lbl_override[dim_or_attrib_id]
    ):
        return lbl_override[dim_or_attrib_id][lang]

    #struct_id = _get_struct_id(structid_or_data_cfg)

    item = _get_dim_or_attrib_from_struct(data_structures, struct_id, dim_or_attrib_id)
    if item is None:
        return dim_or_attrib_id
    return item["name"]


# returns the position of a dimension, used to compose/decompose the data query
def _get_dim_position(data_structures, struct_id, dim_id):
    for idx, d in enumerate(data_structures[struct_id]["dsd"]["dims"]):
        if d["id"] == dim_id:
            return idx
    return -1


def get_code_from_structure_and_dq(data_structures, data_cfg, column_id):
    code_index = _get_dim_position(data_structures, data_cfg["dataflow"], column_id)
    code_id = data_cfg["dq"].split(".")[code_index]

    dim_attr = _get_dim_or_attrib_from_struct(data_structures, data_cfg["dataflow"], column_id)
    if "codes" in dim_attr:
        codelist = dim_attr["codes"]
    else:
        return None
    return next((c for c in codelist if c["id"] == code_id),None)

def get_label_from_structure_and_code(data_structures, data_cfg, column_id, code_id):
    dim_attr = _get_dim_or_attrib_from_struct(data_structures, data_cfg["dataflow"], column_id)
    if "codes" in dim_attr:
        codelist = dim_attr["codes"]
    else:
        return None
    code = next((c for c in codelist if c["id"] == code_id),None)
    return code["name"]


# merge a codes-only dataflow with the codelist
def merge_with_codelist(df, data_structures, struct_id, column_id):
    if not column_id in df.columns:
        return
    cl = _get_dim_or_attrib_from_struct(data_structures, struct_id, column_id)
    if "codes" in cl:  # it is coded
        df_cl = pd.DataFrame(cl["codes"])
        df = df.merge(df_cl, how="left", left_on=column_id, right_on="id")
        dims_to_drop = ["id"]
        if "parent" in df_cl.columns:
            dims_to_drop.append("parent")
        df = df.drop(columns=dims_to_drop)
        df = df.rename(columns={"name": "_L_" + column_id})
    else:
        df["_L_" + column_id] = df[column_id]
    return df


# Multilanguage strings utils


def is_string_empty(container_node, label_id="label"):
    if not label_id in container_node:
        return True
    if isinstance(container_node[label_id], str) and container_node[label_id] == "":
        return True
    if (
        isinstance(container_node[label_id], dict) and not container_node[label_id]
    ):  # is dict empty?
        return True

    return False


def get_multilang_value(label_node, preferred_language="en"):

    if isinstance(label_node, str):
        return label_node
    if isinstance(label_node, dict):
        if preferred_language in label_node:
            return label_node[preferred_language]
        elif "en" in label_node:
            return label_node["en"]

    return list(label_node.values())[0]


def parse_sdmx_data_query(dq: str) -> list:
    return sdmx_data_access.parse_data_query(dq)

def is_float(to_test)->bool:
    if to_test is None:
        return False
    try:
        float(to_test)
        return True
    except ValueError:
        return False

def is_int(to_test)->bool:
    if to_test is None:
        return False
    try:
        int(to_test)
        return True
    except ValueError:
        return False
    
def print_exception(message, exc):
    print(message)
    print("Exception type:")
    print(type(exc))
    print("Exception args:")
    print(exc.args)

def format_num(n):
    if is_int(n):
        ret = "{0:{grp}d}".format(int(n), grp="_")
    elif is_float(n):
        ret = "{0:{grp}g}".format(float(n), grp="_")
    else:
        return n
    return ret.replace("_", " ")

def round_pandas_col(df, col_name, round_to):
    if len(df) == 0:
        return df
    df[col_name] = pd.to_numeric(df[col_name], errors="ignore")
    if pd.api.types.is_numeric_dtype(df[col_name]):
        df = df.round({col_name: round_to})
        if round_to==0:
            df[col_name] = pd.to_numeric(df[col_name], downcast='integer')
    return df