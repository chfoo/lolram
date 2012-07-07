'''reStructuredText document publisher helper'''
#
#    Copyright © 2011-2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Lolram.
#
#    Lolram is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Lolram is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
import collections
import docutils.core
import docutils.io
import docutils.parsers.rst
import docutils.parsers.rst.directives
import docutils.parsers.rst.directives.images
import docutils.utils
import hashlib
import io
import os
import re
import subprocess
import tempfile


__docformat__ = 'restructuredtext en'


class TemplateDirective(docutils.parsers.rst.Directive):
    '''Insert text and replace placeholders
    
    An example template::
        
        Hello {{name}}!
    
    An example document::
    
        .. template: myHelloTemplate
            :name: Jack
    '''

    FIELD_RE = re.compile(r':(\w*):((?:[^\\][^:])*)')
    PLACEHOLDER_RE = re.compile(r'{{(\w+)}}')
    required_arguments = 1
    optional_arguments = 1
    option_spec = {}
    has_content = False
    final_argument_whitespace = True

    def run(self):
        template_name = self.arguments[0]
        template_str = self.get_template_str(template_name)

        if template_str is None:
            raise self.error('Template %s not found' % template_name)

        if len(self.arguments) >= 2:
            substitution_dict = self.parse_content_for_args(template_str)
            text = self.replace_placeholders_with_args(template_str,
                substitution_dict)
        else:
            text = template_str

        self.state_machine.insert_input([text], template_name)
        return []

    def get_template_str(self, template_name):
        fn = self.state.document.settings.restpub_callbacks['template']
        return fn(template_name)

    def parse_content_for_args(self, input_str):
        substituion_dict = {}

        for key, value in re.findall(TemplateDirective.FIELD_RE, input_str):
            substituion_dict[key] = value

        return substituion_dict

    def replace_placeholders_with_args(self, input_str, substitution_dict):
        def f(match):
            key = match.groups()[0]
            return substitution_dict.get(key)

        return re.sub(TemplateDirective.PLACEHOLDER_RE, f, input_str)


class MathDirective(docutils.parsers.rst.Directive):
    '''Insert a math image or return html
    
    Example::
        
        .. math:
            \\sum_{n = 0}^{10} x
    '''

    required_arguments = 0
    optional_arguments = 0
    option_spec = {}
    has_content = True

    def run(self):
        return_list = []
        text = '\n'.join(self.content)
        hex_hash = hashlib.md5(text).hexdigest()
        image_path, mathml, html = self.get_cached_values(hex_hash)

        if not (image_path or html):
            image_path, mathml, html, errors = self.get_values(text)

            if errors:
                return_list.append(docutils.nodes.literal_block(errors,
                    classes=['error']))

        if html:
            return_list.append(docutils.nodes.raw('', html, format='html'))
        elif image_path:
            return_list.append(docutils.nodes.image(image_path, alt=text,
                uri=image_path, classes=['math']))

        return return_list

    def get_cached_values(self, hex_hash):
        f = self.state.document.settings.restpub_callbacks['pre-math']
        result = f(hex_hash)

        if result:
            return result
        else:
            return (None, None, None)

    def get_values(self, text):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_name = temp_dir.name
            p = subprocess.Popen(['texvc', temp_dir_name, temp_dir_name, text,
                'utf8'], stdout=subprocess.PIPE)
            out, err = p.communicate()
            texvc_info = texvc_lexor(out)
            errors = None
            html = None
            image_path = None

            if texvc_info.has_error:
                errors = texvc_info.error_arg
            elif texvc_info.html:
                html = texvc_info.html
            else:
                image_filename = os.path.join(temp_dir_name,
                    '%s.png' % texvc_info.hash)
                image_path = self.state.document.settings \
                    .restpub_callbacks['math'](texvc_info.hash, image_filename)

        return (image_path, None, html, errors)


class ImageDirective(docutils.parsers.rst.directives.images.Image):
    def run(self):
        self.arguments[0] = self.state.document.settings \
            .restpub_callbacks['image'](self.arguments[0])
        return docutils.parsers.rst.directives.images.Image.run(self)


class FigureDirective(docutils.parsers.rst.directives.images.Figure):
    def run(self):
        self.arguments[0] = self.state.document.settings \
            .restpub_callbacks['image'](self.arguments[0])
        return docutils.parsers.rst.directives.images.Figure.run(self)


def format_tree(document):
    if isinstance(document, docutils.nodes.Text):
        return document.astext()
    elif isinstance(document, docutils.nodes.reference):
        return {
            'tag' : document.tagname,
            'values' : [document.attributes.get('refuri')]
        }
    else:
        d = {}
        tag = document.tagname
        d['tag'] = tag
        d['values'] = []
        for child in document.children:
            value = format_tree(child)
            d['values'].append(value)
        return d


docutils.parsers.rst.directives.register_directive('template', TemplateDirective)
docutils.parsers.rst.directives.register_directive('math', MathDirective)
docutils.parsers.rst.directives.register_directive('image', ImageDirective)
docutils.parsers.rst.directives.register_directive('figure', FigureDirective)


class DocInfo(object):
    '''Describes the data return by the RestructuredText parser
    
    :ivar: 
        errors : `str`
            the error text returned by the parser
        title : `str`
            the title of the document without markup
        tree
            a tree with the node values converted to strings
        subtitle : `str`
            the subtitle of the document without markup
        html_parts : `dict`
            the parts of a html document. see http://docutils.sourceforge.net/\
                docs/api/publisher.html#parts-provided-by-the-html-writer
        meta : `dict`
            The metadata of the document such as date and author
    '''

    def __init__(self):
        self.errors = None
        self.title = None
        self.tree = None
        self.subtitle = None
        self.meta = None
        self.refs = None
        self.html_parts = None


def publish_text(text, template_callback=None, math_pre_callback=None,
math_callback=None, image_callback=None, **additional_settings):
    '''Publish text into a RestrucutredText HTML document
    
    :parameters:
        text : `str`
            The input text
        template_callback
            This function will be called when a template is requested::
            
                def template_callback(`str` name):
                    return `str` template_text_content
            
        math_pre_callback
            This function is called before generation of math images
            
            def math_pre_callback(md5_hex):
                return src
        
        math_callback
            This function will be called when mathematics is created::
            
                def math_callback(md5_hash, image_filename):
                    return `str` image_path
            
            It is your responsibility for caching the image.
        
        image_callback
            This function will be called when an image is requested::
            
            def image_callback(`str` image_filename):
                return `str` new_image_filename
        
    :rtype: `DocInfo`
    '''

    error_stream = io.StringIO()
    settings = {
        'halt_level' : 5,
        'warning_stream' : error_stream,
        'file_insertion_enabled' : False,
        'raw_enabled' : False,
        'restpub_callbacks': {
            'template': template_callback,
            'math': math_callback,
            'image': image_callback,
            'pre-math': math_pre_callback,
        },
        'restpub_additional_settings': additional_settings,
    }

    output, publisher = docutils.core.publish_programmatically(
        source_class=docutils.io.StringInput, source=text,
        source_path=None,
        destination_class=docutils.io.NullOutput, destination=None,
        destination_path=docutils.io.NullOutput.default_destination_path,
        reader=None, reader_name='standalone',
        parser=None, parser_name='restructuredtext',
        writer=None, writer_name='html',
        settings=None, settings_spec=None, settings_overrides=settings,
        config_section=None, enable_exit_status=None)

    document = publisher.writer.document
    doc_info = DocInfo()
    doc_info.tree = format_tree(document)
    error_stream.seek(0)
    doc_info.errors = error_stream.read()
    doc_info.title = document.get('title')
    doc_info.subtitle = document.get('subtitle')

    if not doc_info.subtitle:
        for element in document:
            if element.tagname == 'subtitle':
                doc_info.subtitle = element.astext()

    doc_info.meta = {}
    i = publisher.document.first_child_matching_class(docutils.nodes.docinfo)
    if i is not None:
        docinfo = document[i]

        for node in docinfo:
            doc_info.meta[node.tagname] = node.astext()

    # TODO: get references working
#    doc_info['refs'] = {}
#    for name, node_list in document.refnames.iteritems():
#        doc_info['refs'][name] = map(format_tree, node_list)

    doc_info.html_parts = publisher.writer.parts

    return doc_info


TexVCInfo = collections.namedtuple('TexVCInfo',
    ['code', 'hash', 'html', 'mathml', 'has_error', 'error_arg'])

def texvc_lexor(s):
    '''Lexes the output from texvc
    
    :paramters:
        s: `byte`
            The output from texvc
    
    :rtype: `TexVCInfo`
    '''

    code = s[0].decode()
    has_error = code in ('S', 'E', 'F', '-')
    mathml = None
    html = None
    hash = None
    error_arg = None

    if code == 'F':
        error_arg = s[1:].decode()

    if not has_error:
        hash = s[1:1 + 32].decode()

        if code == 'X':
            mathml = s[33:].decode()
        else:
            html, nul, mathml = s[33:].partition(b'\x00')
            html = html.decode()
            mathml = mathml.decode()
            del nul

    t = TexVCInfo(code=code, has_error=has_error, mathml=mathml,
        html=html, hash=hash, error_arg=error_arg)
    return t
