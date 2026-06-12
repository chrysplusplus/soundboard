import http.server
import json
import socketserver

from dataclasses import dataclass, fields
from http import HTTPStatus

PORT = 8000

HTML_TEMPLATE = """
<html>
    <head>
        <title>Soundboard</title>
    </head>
    <body>
        <p>Hello, World!</p>
    </body>
</html>
"""

@dataclass
class SItem:
    type: str
    text: str

@dataclass
class Soundboard:
    title: str
    items: [SItem]

@dataclass
class DataFile:
    version: int
    soundboard: Soundboard

class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    '''HTTP Request Handler class for server'''
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_TEMPLATE.encode())

def datafile_obj_parse_cls(data: dict, cls: type) -> object:
    '''`cls` must be a dataclass instance'''
    for field in fields(cls):
        if field.name not in data:
            return data

        value = data.get(field.name)
        if type(field.type) == list and type(value) == list:
            contained_type = field.type[0]
            for elem in value:
                if type(elem) != contained_type:
                    return data

        elif type(field.type) == list:
            return data

        elif not isinstance(value, field.type):
            return data

    return cls(**data)

KNOWN_DATAFILE_CLS = (SItem, Soundboard, DataFile)

def datafile_objhk(data: dict) -> object:
    '''Detect and parse json data into datafile class objects'''
    for cls in KNOWN_DATAFILE_CLS:
        result = datafile_obj_parse_cls(data, cls)
        if result is not data:
            return result

    return data

def main():
    data: dict
    with open("example.json", 'r') as datafile:
        data = json.load(datafile, object_hook = datafile_objhk)

    with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Running server on port {PORT}...")
        httpd.serve_forever()

if __name__ == "__main__":
    main()

