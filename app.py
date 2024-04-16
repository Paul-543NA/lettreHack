import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash import dash_table

from utils.api import fetch_letters

# Set a darker theme for the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

letters_data = fetch_letters()

app.layout = html.Div([
    html.H1("Letters Dashboard"),
    # Add a bit of space before the tabl
    html.Br(),
    dash_table.DataTable(
        id='table',
        columns=[
            {"name": "Date", "id": "data_sent"},
            {"name": "Sender", "id": "sender"},
            {"name": "Transcript", "id": "transcript"},
            {"name": "Summary", "id": "summary"},
            {"name": "Recommended Department", "id": "recommended_department"},
        ],
        data=[letters_data[lid] for lid in letters_data.keys()],
        style_table={'maxWidth': '100%', 'overflowY': 'auto', 'overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'normal',
            'height': 'auto',
            'textAlign': 'left',
            'padding': '5px',
        },
        style_data={
            'width': '150px', 'maxWidth': '150px', 'minWidth': '150px',
        },
        style_header={
            'fontWeight': 'bold'
        }
    ),

    # Upload component
    html.Div([
        dcc.Upload(
            id='upload-image',
            children=html.Button('Upload Image'),
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
            # Allow multiple files to be uploaded
            multiple=True
        ),
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
    print(list_of_contents)
    if list_of_contents is not None:
        children = [
            html.Div("File uploaded successfully!")
        ]
        return children


if __name__ == '__main__':
    app.run_server(debug=True)