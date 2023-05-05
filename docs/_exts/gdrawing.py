# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
import datetime
from docutils.nodes import raw
import requests
import os

class GDrawing(Directive):
    required_arguments = 1

    def run(self):
        drawing_id = self.arguments[0]
        response = requests.get(f'https://docs.google.com/drawings/export/svg?id={drawing_id}')
        img_path = os.path.join(self.state.document.settings.env.app.outdir, '_static', 'img', drawing_id + ".svg")
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        with open(img_path, 'wb') as f:
            f.write(response.content)
        return [raw('', '<img src="{}"></img>'.format(img_path), format='html')]

def setup(app):
    app.add_directive('gdrawing', GDrawing)
