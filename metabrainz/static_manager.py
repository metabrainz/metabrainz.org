import os.path
import json


manifest_content = {}


def read_manifest(app):
    manifest_path = os.path.join(app.config["STATIC_RESOURCES_DIR"], "dist", "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path) as manifest_file:
            global manifest_content
            manifest_content = json.load(manifest_file)


def get_static_path(resource_name):
    if resource_name not in manifest_content:
        return "/static/%s" % resource_name
    return manifest_content[resource_name]
