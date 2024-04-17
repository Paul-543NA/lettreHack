import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash import dash_table

from utils.api import fetch_letters
from utils.upload_process import upload_image

import json
import firebase_admin
from firebase_admin import credentials, db
from pathlib import Path

from base64 import b64decode

# LOADS EVERYTHING FIREBASE RELATED

private_keys = json.load(open("credentials.json"))
FIRESTORE_URL = private_keys["FIRESTORE_URL"]

cred_file_path = Path("./firebase_key.json")
cred = credentials.Certificate(cred_file_path)

firebase_admin.initialize_app(
    cred, {"databaseURL": FIRESTORE_URL}
)

# Set a darker theme for the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

letters_data = fetch_letters()

def get_letter_markdown_dict(letter_dict):
    presentation_dict = {}
    for key, value in letter_dict.items():
        presentation_dict[key] = value
        presentation_dict[key]["Description"] = f"""**[[{value['date']}] {value['subject']}]({value['image_url']})**
*From {value['sender']} to {value['recipient']}*

Summary: {value['summary']}
"""
        presentation_dict[key]["Triage"] = f"**{value['Departments']} - Justification:** {value['Department_Justification']}"
    return presentation_dict

presentation_dict = get_letter_markdown_dict(letters_data)

app.layout = html.Div([
    html.H1("Letters Dashboard"),
    # Add a bit of space before the tabl
    html.Br(),
    dcc.Upload(
        id='upload-image',
        children=html.Button('Upload Image', style={'width': '100%', 'height': '100%'}),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=True
    ),
    html.Div(id='output-image-upload'),

    dash_table.DataTable(
        id='table',
        columns=[
            {'name': 'Description', 'id': 'Description', "presentation": "markdown"},
            {'name': 'Triage', 'id': 'Triage', "presentation": "markdown"},
        ],
        data=[presentation_dict[lid] for lid in presentation_dict.keys()],
        style_table={'maxWidth': '100%', 'overflowY': 'auto', 'overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'normal',
            'height': 'auto',
            'textAlign': 'left',
            'padding': '5px',
        },
        style_header={
            'fontWeight': 'bold'
        },
        page_action='native',  # Enable pagination
        page_size=10,
    ),

    # Upload component
    html.Div([
        html.Div(id='output-image-upload'),
    ])

], style={'padding': '20px'})


# Callback to handle uploaded images
@app.callback(
    Output('output-image-upload', 'children'),
    Input('upload-image', 'contents'),
    prevent_initial_call=True
)
def update_output(list_of_contents):
    if list_of_contents is not None:
        for content in list_of_contents:
            content_type, content_string = content.split(',')
            content_bytes = b64decode(content_string)
            upload_image(content_bytes)

if __name__ == '__main__':
    app.run_server(debug=True)