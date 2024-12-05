import os.path
import json

from flask import current_app

MANIFEST_PATH = os.path.join("/", "static", "dist", "manifest.json")

manifest_content = {}


def read_manifest():
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as manifest_file:
            global manifest_content
            manifest_content = json.load(manifest_file)


def get_static_path(resource_name):
    if resource_name not in manifest_content:
        return current_app.config["OAUTH2_BLUEPRINT_PREFIX"] + "/static/%s" % resource_name
    return current_app.config["OAUTH2_BLUEPRINT_PREFIX"] + manifest_content[resource_name]
